import Foundation

enum DTCCatalog {
    private static let descriptions: [String: String] = {
        guard let url = Bundle.main.url(forResource: "dtc_codes", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let values = try? JSONDecoder().decode([String: String].self, from: data) else {
            return [:]
        }
        return values
    }()

    static func description(for code: String) -> String {
        descriptions[code.uppercased()] ?? "Description unavailable"
    }
}
