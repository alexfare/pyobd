import XCTest
@testable import PyOBDMobile

final class OBDParserTests: XCTestCase {
    func testRecordedRPMResponse() {
        let reading = StandardPID.engineRPM.reading(from: "010C\r41 0C 1A F8\r>")
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 1726, accuracy: 0.001)
        XCTAssertEqual(reading?.unit, "RPM")
    }

    func testRecordedCoolantResponse() {
        let reading = StandardPID.coolantTemperature.reading(from: "41 05 7B\r>")
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 83, accuracy: 0.001)
    }

    func testRecordedFreezeFrameResponse() {
        let reading = StandardPID.vehicleSpeed.reading(
            from: "42 0D 00 37\r>",
            responseMode: 0x42,
            frame: 0x00
        )
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 55, accuracy: 0.001)
    }

    func testRecordedTroubleCodeResponses() {
        XCTAssertEqual(
            OBDParser.troubleCodes(in: "43 01 33 03 00 00 00\r>", responseMode: 0x43),
            ["P0133", "P0300"]
        )
        XCTAssertEqual(
            OBDParser.troubleCodes(in: "47 04 56 00 00\r>", responseMode: 0x47),
            ["P0456"]
        )
    }

    func testPIDCatalogUsesReadableNames() {
        XCTAssertEqual(Mode01PIDCatalog.name(for: 0x0C), "Engine RPM")
        XCTAssertEqual(Mode01PIDCatalog.name(for: 0x42), "Control Module Voltage")
    }
}
