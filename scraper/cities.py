"""All 34 incorporated cities in Orange County, CA."""

CITIES = [
    {"name": "Aliso Viejo", "slug": "aliso-viejo"},
    {"name": "Anaheim", "slug": "anaheim"},
    {"name": "Brea", "slug": "brea"},
    {"name": "Buena Park", "slug": "buena-park"},
    {"name": "Costa Mesa", "slug": "costa-mesa"},
    {"name": "Cypress", "slug": "cypress"},
    {"name": "Dana Point", "slug": "dana-point"},
    {"name": "Fountain Valley", "slug": "fountain-valley"},
    {"name": "Fullerton", "slug": "fullerton"},
    {"name": "Garden Grove", "slug": "garden-grove"},
    {"name": "Huntington Beach", "slug": "huntington-beach"},
    {"name": "Irvine", "slug": "irvine"},
    {"name": "Laguna Beach", "slug": "laguna-beach"},
    {"name": "Laguna Hills", "slug": "laguna-hills"},
    {"name": "Laguna Niguel", "slug": "laguna-niguel"},
    {"name": "Laguna Woods", "slug": "laguna-woods"},
    {"name": "Lake Forest", "slug": "lake-forest"},
    {"name": "La Habra", "slug": "la-habra"},
    {"name": "La Palma", "slug": "la-palma"},
    {"name": "Los Alamitos", "slug": "los-alamitos"},
    {"name": "Mission Viejo", "slug": "mission-viejo"},
    {"name": "Newport Beach", "slug": "newport-beach"},
    {"name": "Orange", "slug": "orange"},
    {"name": "Placentia", "slug": "placentia"},
    {"name": "Rancho Santa Margarita", "slug": "rancho-santa-margarita"},
    {"name": "San Clemente", "slug": "san-clemente"},
    {"name": "San Juan Capistrano", "slug": "san-juan-capistrano"},
    {"name": "Santa Ana", "slug": "santa-ana"},
    {"name": "Seal Beach", "slug": "seal-beach"},
    {"name": "Stanton", "slug": "stanton"},
    {"name": "Tustin", "slug": "tustin"},
    {"name": "Villa Park", "slug": "villa-park"},
    {"name": "Westminster", "slug": "westminster"},
    {"name": "Yorba Linda", "slug": "yorba-linda"},
]


def query_location(city_name: str) -> str:
    return f"{city_name}, CA"
