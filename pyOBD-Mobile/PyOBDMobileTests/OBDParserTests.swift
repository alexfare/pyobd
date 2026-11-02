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

    func testRecordedFuelTrimResponse() {
        let reading = StandardPID.shortFuelTrimBank1.reading(from: "41 06 90\r>")
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 12.5, accuracy: 0.001)
    }

    func testRecordedMassAirFlowResponse() {
        let reading = StandardPID.massAirFlow.reading(from: "41 10 01 F4\r>")
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 5, accuracy: 0.001)
        XCTAssertEqual(reading?.unit, "g/s")
    }

    func testRecordedOilTemperatureResponse() {
        let reading = StandardPID.engineOilTemperature.reading(from: "41 5C 82\r>")
        XCTAssertNotNil(reading)
        XCTAssertEqual(reading!.value, 90, accuracy: 0.001)
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

    func testPollingRates() {
        XCTAssertNil(PIDPollingRate.off.interval)
        XCTAssertEqual(PIDPollingRate.slow.interval, 2)
        XCTAssertEqual(PIDPollingRate.normal.interval, 0.5)
        XCTAssertEqual(PIDPollingRate.fast.interval, 0.15)
    }
}
