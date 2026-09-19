import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import csv
import time


BASE_URLS = [
   "https://www.escapadarural.com"
]

MAX_PAGES = 50
CRAWL_DELAY = 0.3
REQUEST_TIMEOUT = 5
USER_AGENT = "Mozilla/5.0 (compatible; LegalContactAuditBot/1.0)"

MAX_EXTERNAL_PER_PAGE = 3
MAX_WORKERS = 3

HEADERS = {"User-Agent": USER_AGENT}

PHONE_REGEX = re.compile(
    r"(?:(?:\+34|0034)\s?)?(?:6|7|8|9)\d{2}[\s.-]?\d{3}[\s.-]?\d{3}"
)

POSTAL_REGEX = re.compile(r"\b\d{5}\b")

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

BLOCKED_EXTERNAL_DOMAINS = [
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "twitter.com", "x.com", "google.com", "maps.google",
    "wa.me", "whatsapp.com", "booking.com", "airbnb.com",
    "tripadvisor.", "escapadarural.com", "sensacionrural.es"
]

CONTACT_PATHS = [
    "",
    "/contacto",
    "/contact",
    "/legal",
    "/aviso-legal",
    "/privacidad",
    "/privacy",
    "/sobre-nosotros",
    "/about"
]




def normalize_url(url):
    if not url:
        return ""

    url, _ = urldefrag(url)
    parsed = urlparse(url)

    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return f"{scheme}://{netloc}{path}"


def get_domain(url):
    return urlparse(url).netloc.lower()


def is_same_domain(url, base_domain):
    domain = get_domain(url)
    return domain == base_domain or domain.endswith("." + base_domain)


def clean_text(text):
    return " ".join(text.split()).strip()


def is_property_page(url):
    return bool(re.search(r"_\d+$", url))


def safe_request(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        print(
            f"[HTTP {response.status_code}] "
            f"{url} -> {response.url}"
        )

        if response.status_code >= 400:
            return None

        return response

    except requests.RequestException as error:
        print(f"[ERROR REQUEST] {url} -> {error}")
        return None
    
def is_blocked_external(url):
    domain = get_domain(url)
    return any(blocked in domain for blocked in BLOCKED_EXTERNAL_DOMAINS)


def get_base_site(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_emails(text, soup=None):
    emails = set()

    for email in EMAIL_REGEX.findall(text):
        emails.add(email.lower())

    if soup:
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()

            if href.lower().startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0].strip()

                if EMAIL_REGEX.match(email):
                    emails.add(email.lower())

    return sorted(emails)


def extract_phones(text, soup=None):
    phones = set()

    for phone in PHONE_REGEX.findall(text):
        phones.add(clean_text(phone))

    if soup:
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()

            if href.lower().startswith("tel:"):
                phone = href.replace("tel:", "").strip()
                phone = clean_text(phone)

                if phone:
                    phones.add(phone)

    return sorted(phones)


def extract_addresses(text):
    addresses = set()

    patterns = [
        r"\b(?:C\/|Calle|Carrer|Avenida|Av\.|Avinguda|Plaza|Plaça|Camino|Carretera|Paseo|Rúa|Travesía)\s+[^.;|]{3,80}?\b\d{5}\b[^.;|]{0,60}",
        r"\b\d{5}\s+[A-ZÁÉÍÓÚÑ][^.;|]{3,60}",
        r"\b(?:Lugar|Barrio|Aldea|Paraje|Finca)\s+[^.;|]{3,80}?\b\d{5}\b[^.;|]{0,60}",
    ]

    bad_words = [
        "reseñas", "google", "media", "opiniones", "valoración",
        "total reseñas", "resumen", "política de privacidad",
        "acepto", "enviar", "contacta", "página no encontrada"
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            candidate = clean_text(match)

            if any(bad in candidate.lower() for bad in bad_words):
                continue

            if len(candidate) <= 120:
                addresses.add(candidate)

    return sorted(addresses)


def extract_external_websites(current_url, soup, base_domain):
    websites = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()

        if not href:
            continue

        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue

        full_url = normalize_url(urljoin(current_url, href))

        if not full_url.startswith("http"):
            continue

        if is_same_domain(full_url, base_domain):
            continue

        if is_blocked_external(full_url):
            continue

        websites.add(get_base_site(full_url))

    return sorted(websites)[:MAX_EXTERNAL_PER_PAGE]


def extract_contact_from_external_site(external_url):
    base = get_base_site(external_url)

    emails = set()
    phones = set()
    addresses = set()

    for path in CONTACT_PATHS[:4]:
        page_url = normalize_url(base + path)

        response = safe_request(page_url)
        time.sleep(CRAWL_DELAY)

        if response is None:
            continue

        if "text/html" not in response.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        text = clean_text(soup.get_text(" ", strip=True))

        emails.update(extract_emails(text, soup))
        phones.update(extract_phones(text, soup))
        addresses.update(extract_addresses(text))

    return {
        "external_url": base,
        "emails": sorted(emails),
        "phones": sorted(phones),
        "addresses": sorted(addresses)
    }


def extract_name_from_url(url):
    slug = url.split("/")[-1]
    slug = re.sub(r"_\d+$", "", slug)
    name = slug.replace("-", " ").strip()
    return name.title()


def extract_city_from_url(url):
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/") if path else []

        # /casas-rurales/tenerife
        if len(parts) >= 2 and parts[0] == "casas-rurales":
            city = parts[1]
            return city.replace("-", " ").title()

        # /casa-rural/sevilla/casaruralsevilla
        # /casa-rural/girona/apartamento-del-ferrer
        if len(parts) >= 2 and parts[0] == "casa-rural":
            city = parts[1]
            return city.replace("-", " ").title()

        # /casas-rurales-en-jaca
        match = re.search(r"casas-rurales-en-([a-záéíóúñ-]+)", path, re.IGNORECASE)
        if match:
            return match.group(1).replace("-", " ").title()

    except Exception:
        pass

    return ""

        

def extract_country():
    return "España"


def extract_postal_code(text):
    match = POSTAL_REGEX.search(text)
    return match.group(0) if match else ""

def extract_city_from_address(text):
    match = re.search(r"\b\d{5}\s+([A-Za-zÁÉÍÓÚÑáéíóúñ\s-]{2,40})", text)

    if match:
        return clean_text(match.group(1))

    parts = re.split(r",|-", text)

    for part in parts:
        part = part.strip()

        if part and part[0].isupper() and len(part.split()) <= 3:
            return part

    return ""



    if not addresses:
        return {
            "postal_code": "",
            "city": "",
            "country": "España"
        }

    for addr in addresses:
        postal = extract_postal_code(addr)
        city = extract_city_from_address(addr)

        if postal or city:
            return {
                "postal_code": postal,
                "city": city,
                "country": "España"
            }

    return {
        "postal_code": "",
        "city": "",
        "country": "España"
    }


def normalize_location(addresses):
    if not addresses:
        return {
            "address": "",
            "postal_code": "",
            "city": "",
            "country": "España"
        }

    for addr in addresses:
        postal = extract_postal_code(addr)
        city = extract_city_from_address(addr)

        if postal or city:
            return {
                "address": addr,
                "postal_code": postal,
                "city": city,
                "country": "España"
            }

    return {
        "address": addresses[0] if addresses else "",
        "postal_code": "",
        "city": "",
        "country": "España"
    }

def print_result(row):
    print("\n" + "=" * 80)
    print(f"URL: {row['url']}")

    if row["phones"]:
        print("TELÉFONOS:")
        for phone in row["phones"]:
            print(f"  - {phone}")

    location = normalize_location(row["addresses"])
    city = extract_city_from_url(row["url"]) or location["city"]

    if location["postal_code"] or city:
        print("UBICACIÓN:")
        print(f"  - Ciudad: {city}")
        print(f"  - CP: {location['postal_code']}")
        print(f"  - País: {location['country']}")

    if row["emails"]:
        print("EMAILS:")
        for email in row["emails"]:
            print(f"  - {email}")

    if row["external_contacts"]:
        print("CONTACTOS EN WEBS EXTERNAS:")

        for external in row["external_contacts"]:
            print(f"  Web: {external['external_url']}")

            if external["phones"]:
                print("    Teléfonos:")
                for phone in external["phones"]:
                    print(f"      - {phone}")

            if external["addresses"]:
                print("    Direcciones:")
                for address in external["addresses"]:
                    print(f"      - {address}")

            if external["emails"]:
                print("    Emails:")
                for email in external["emails"]:
                    print(f"      - {email}")

    print("=" * 80)


def crawl_contacts(base_url):
    base_url = normalize_url(base_url)
    base_domain = get_domain(base_url)

    queue = deque([base_url])
    visited = set()
    results = []

    while queue and len(visited) < MAX_PAGES:
        current_url = normalize_url(queue.popleft())

        if current_url in visited:
            continue

        visited.add(current_url)
        print(f"[{len(visited)}/{MAX_PAGES}] Visitando: {current_url}")

        response = safe_request(current_url)
        time.sleep(CRAWL_DELAY)

        if response is None:
            continue

        if "text/html" not in response.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        text = clean_text(soup.get_text(" ", strip=True))

        emails = extract_emails(text, soup)
        phones = extract_phones(text, soup)
        addresses = extract_addresses(text)

        external_webs = []
        external_contacts = []

        if is_property_page(current_url):
            external_webs = extract_external_websites(
                current_url,
                soup,
                base_domain
            )

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(extract_contact_from_external_site, web): web
                    for web in external_webs
                }

                for future in as_completed(futures):
                    web = futures[future]

                    try:
                        contact_data = future.result()
                        external_contacts.append(contact_data)

                    except Exception as e:
                        print(f"[ERROR WEB EXTERNA] {web} -> {e}")

        has_data = (
            emails
            or phones
            or addresses
            or any(
                e["emails"] or e["phones"] or e["addresses"]
                for e in external_contacts
            )
        )

        if has_data:
            row = {
                "url": current_url,
                "phones": phones,
                "addresses": addresses,
                "emails": emails,
                "external_webs": external_webs,
                "external_contacts": external_contacts
            }

            results.append(row)
            print_result(row)

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()

            if not href:
                continue

            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            full_url = normalize_url(urljoin(current_url, href))

            if is_same_domain(full_url, base_domain):
                if full_url not in visited and full_url not in queue:
                    queue.append(full_url)

    return results


def save_csv(data):
    with open("results_clean.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "nombre",
            "ciudad",
            "codigo_postal",
            "pais",
            "telefono",
            "email",
            "direccion",
            "web_externa",
            "telefono_ext",
            "email_ext",
            "direccion_ext",
            "url_origen"
        ])

        for row in data:
            nombre = extract_name_from_url(row["url"])
            ciudad = extract_city_from_url(row["url"])
            pais = extract_country()

            telefono = row["phones"][0] if row["phones"] else ""
            email = row["emails"][0] if row["emails"] else ""

            location = normalize_location(row["addresses"])

            city = location["city"].strip()
            if not city:
                city = extract_city_from_url(row["url"])
            codigo_postal = location["postal_code"]
            direccion = location["address"]

            web_externa = ""
            telefono_ext = ""
            email_ext = ""
            direccion_ext = ""

            if row["external_contacts"]:
                ext = row["external_contacts"][0]

                web_externa = ext["external_url"]
                telefono_ext = ext["phones"][0] if ext["phones"] else ""
                email_ext = ext["emails"][0] if ext["emails"] else ""
                direccion_ext = ext["addresses"][0] if ext["addresses"] else ""

            writer.writerow([
                nombre,
                ciudad,
                codigo_postal,
                pais,
                telefono,
                email,
                direccion,
                web_externa,
                telefono_ext,
                email_ext,
                direccion_ext,
                row["url"]
            ])


def main():
    all_data = []

    for url in BASE_URLS:
        print(f"\n===== INICIANDO CRAWL EN: {url} =====")
        data = crawl_contacts(url)
        all_data.extend(data)

    save_csv(all_data)

    print("\n✔ DONE")
    print(f"Resultados totales: {len(all_data)}")
    print("Archivo guardado: results_clean.csv")


if __name__ == "__main__":
    main()
