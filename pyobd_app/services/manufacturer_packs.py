"""Verification and decryption for manufacturer PID packs."""

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from uuid import uuid4


PACK_FORMAT = "pyobd-manufacturer-pack"
LICENSE_FORMAT = "pyobd-pack-license"


class ManufacturerPackError(ValueError):
    pass


class ManufacturerPackRegistry:
    def __init__(self, directory=None, trusted_keys=None):
        self.directory = Path(directory) if directory else Path.home() / ".pyobd"
        self.pack_directory = self.directory / "packs"
        self.license_directory = self.directory / "licenses"
        try:
            self.pack_directory.mkdir(parents=True, exist_ok=True)
            self.license_directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.device_id = self._installation_id()
        self._trusted_keys = (
            trusted_keys if trusted_keys is not None else self._load_trusted_keys()
        )
        self._packs = {}
        self._licenses = {}
        self.refresh()

    @property
    def owned_pack_ids(self):
        return set(self._packs).intersection(self._licenses)

    def is_entitled(self, pack_id, minimum_version=""):
        pack_id = self._normalized_pack_id(pack_id)
        pack = self._packs.get(pack_id)
        license_payload = self._licenses.get(pack_id)
        if pack is None or license_payload is None:
            return False
        version = pack.get("manifest", {}).get("version", "")
        if minimum_version and self._version(version) < self._version(minimum_version):
            return False
        return True

    def install_pack(self, source):
        source = Path(source)
        document = self._read_document(source)
        manifest = self._verified_pack_manifest(document)
        pack_id = self._normalized_pack_id(manifest["pack_id"])
        version = str(manifest["version"]).strip()
        destination = self.pack_directory / "{}-{}.pyobd-pack".format(pack_id, version)
        shutil.copy2(source, destination)
        self.refresh()
        return pack_id

    def install_license(self, source):
        source = Path(source)
        document = self._read_document(source)
        entitlement = self._verified_entitlement(document)
        pack_id = self._normalized_pack_id(entitlement["pack_id"])
        destination = self.license_directory / "{}.pyobd-license".format(pack_id)
        shutil.copy2(source, destination)
        self.refresh()
        return pack_id

    def refresh(self):
        self._packs = {}
        self._licenses = {}
        for path in self.pack_directory.glob("*.pyobd-pack"):
            try:
                document = self._read_document(path)
                manifest = self._verified_pack_manifest(document)
                pack_id = self._normalized_pack_id(manifest["pack_id"])
                current = self._packs.get(pack_id, {}).get("manifest", {}).get("version", "")
                if not current or self._version(manifest["version"]) > self._version(current):
                    self._packs[pack_id] = document
            except (OSError, ValueError, KeyError, ManufacturerPackError):
                continue
        for path in self.license_directory.glob("*.pyobd-license"):
            try:
                document = self._read_document(path)
                entitlement = self._verified_entitlement(document)
                self._licenses[self._normalized_pack_id(entitlement["pack_id"])] = entitlement
            except (OSError, ValueError, KeyError, ManufacturerPackError):
                continue

    def definitions(self, pack_id):
        pack_id = self._normalized_pack_id(pack_id)
        if not self.is_entitled(pack_id):
            raise ManufacturerPackError("A valid pack and license are required")
        document = self._packs[pack_id]
        manifest = self._verified_pack_manifest(document)
        entitlement = self._licenses[pack_id]
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = base64.b64decode(entitlement["content_key"], validate=True)
            nonce = base64.b64decode(document["nonce"], validate=True)
            ciphertext = base64.b64decode(document["ciphertext"], validate=True)
            plaintext = AESGCM(key).decrypt(
                nonce, ciphertext, self._canonical_bytes(manifest)
            )
        except Exception as error:
            raise ManufacturerPackError("Unable to decrypt manufacturer pack") from error
        expected_hash = str(manifest.get("payload_sha256", "")).lower()
        if not expected_hash or hashlib.sha256(plaintext).hexdigest() != expected_hash:
            raise ManufacturerPackError("Manufacturer pack integrity check failed")
        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ManufacturerPackError("Manufacturer pack payload is invalid") from error
        if not isinstance(payload, dict):
            raise ManufacturerPackError("Manufacturer pack payload is invalid")
        return payload

    def _verified_pack_manifest(self, document):
        if document.get("format") != PACK_FORMAT or document.get("version") != 1:
            raise ManufacturerPackError("Unsupported manufacturer pack")
        manifest = document.get("manifest")
        if not isinstance(manifest, dict):
            raise ManufacturerPackError("Manufacturer pack manifest is missing")
        signed = {
            "format": document["format"],
            "version": document["version"],
            "key_id": document.get("key_id", ""),
            "manifest": manifest,
            "nonce": document.get("nonce", ""),
            "ciphertext": document.get("ciphertext", ""),
        }
        self._verify_signature(document, signed)
        self._normalized_pack_id(manifest.get("pack_id", ""))
        if not str(manifest.get("version", "")).strip():
            raise ManufacturerPackError("Manufacturer pack version is missing")
        return manifest

    def _verified_entitlement(self, document):
        if document.get("format") != LICENSE_FORMAT or document.get("version") != 1:
            raise ManufacturerPackError("Unsupported pack license")
        entitlement = document.get("entitlement")
        if not isinstance(entitlement, dict):
            raise ManufacturerPackError("Pack entitlement is missing")
        signed = {
            "format": document["format"],
            "version": document["version"],
            "key_id": document.get("key_id", ""),
            "entitlement": entitlement,
        }
        self._verify_signature(document, signed)
        self._normalized_pack_id(entitlement.get("pack_id", ""))
        device_id = str(entitlement.get("device_id", ""))
        if device_id != self.device_id:
            raise ManufacturerPackError("Pack license belongs to another installation")
        expires = str(entitlement.get("expires", "")).strip()
        if expires:
            try:
                expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except ValueError as error:
                raise ManufacturerPackError("Pack license expiry is invalid") from error
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                raise ManufacturerPackError("Pack license has expired")
        try:
            key = base64.b64decode(entitlement["content_key"], validate=True)
        except (KeyError, ValueError, TypeError) as error:
            raise ManufacturerPackError("Pack license key is invalid") from error
        if len(key) not in (16, 24, 32):
            raise ManufacturerPackError("Pack license key is invalid")
        return entitlement

    def _verify_signature(self, document, signed):
        key_id = str(document.get("key_id", ""))
        encoded_key = self._trusted_keys.get(key_id)
        if not encoded_key:
            raise ManufacturerPackError("Pack signer is not trusted")
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            public_key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(encoded_key, validate=True)
            )
            public_key.verify(
                base64.b64decode(document["signature"], validate=True),
                self._canonical_bytes(signed),
            )
        except (ImportError, KeyError, ValueError, TypeError) as error:
            raise ManufacturerPackError("Manufacturer pack signature is invalid") from error
        except Exception as error:
            raise ManufacturerPackError("Manufacturer pack signature is invalid") from error

    def _installation_id(self):
        path = self.directory / "installation-id"
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value:
            return value
        value = uuid4().hex
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
        except OSError:
            pass
        return value

    def _load_trusted_keys(self):
        path = Path(__file__).resolve().parent.parent / "resources" / "trusted_pack_keys.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {
            str(key_id): str(public_key)
            for key_id, public_key in payload.items()
            if str(key_id).strip() and str(public_key).strip()
        } if isinstance(payload, dict) else {}

    @staticmethod
    def _read_document(path):
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ManufacturerPackError("Manufacturer pack file is too large")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ManufacturerPackError("Manufacturer pack file is invalid")
        return payload

    @staticmethod
    def _canonical_bytes(value):
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @staticmethod
    def _normalized_pack_id(value):
        value = str(value).strip().lower()
        if not value or len(value) > 128 or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
            for character in value
        ):
            raise ManufacturerPackError("Manufacturer pack ID is invalid")
        return value

    @staticmethod
    def _version(value):
        parts = []
        for part in str(value).split(".")[:3]:
            digits = "".join(character for character in part if character.isdigit())
            parts.append(int(digits or 0))
        return tuple((parts + [0, 0, 0])[:3])
