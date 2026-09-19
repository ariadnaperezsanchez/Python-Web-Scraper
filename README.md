# Python Web Scraper

A Python web scraping project designed to crawl rural accommodation pages and extract publicly available contact information.

The project uses **Requests** and **BeautifulSoup** to navigate web pages, collect contact details, explore relevant external websites, and export the extracted information to a CSV file.

## Features

- Crawls rural accommodation pages
- Extracts phone numbers
- Extracts email addresses
- Detects postal addresses
- Identifies city and postal code information
- Detects external accommodation websites
- Searches external websites for additional contact information
- Filters unwanted external domains
- Uses multithreading to process external websites
- Exports collected data to CSV
- Includes configurable crawling limits and request delays
- Displays crawling progress in the terminal

## Technologies

- Python 3
- Requests
- BeautifulSoup4
- Regular Expressions
- CSV
- ThreadPoolExecutor
- urllib

## Project Structure

```text
Python-Web-Scraper/
├── scraper.py
├── requirements.txt
├── README.md
└── .gitignore
```

The generated CSV file is excluded from Git version control.

## Installation

Clone the repository:

```bash
git clone https://github.com/ariadnaperezsanchez/Python-Web-Scraper.git
cd Python-Web-Scraper
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the scraper with:

```bash
python3 scraper.py
```

While running, the program displays the pages being visited and their HTTP response status.

Example:

```text
===== INICIANDO CRAWL EN: https://www.escapadarural.com =====

[1/50] Visitando: https://www.escapadarural.com/
[HTTP 200] ...
```

When the crawling process finishes, the extracted information is stored in:

```text
results_clean.csv
```

## Extracted Data

The generated CSV can contain the following fields:

| Field | Description |
|---|---|
| `nombre` | Name derived from the accommodation URL |
| `ciudad` | City |
| `codigo_postal` | Postal code |
| `pais` | Country |
| `telefono` | Phone number |
| `email` | Email address |
| `direccion` | Postal address |
| `web_externa` | External website |
| `telefono_ext` | Phone found on external website |
| `email_ext` | Email found on external website |
| `direccion_ext` | Address found on external website |
| `url_origen` | Original page where the information was discovered |

## How It Works

The scraper starts from a configured base URL and explores relevant internal pages.

For each page, it:

1. Sends an HTTP request.
2. Parses the HTML using BeautifulSoup.
3. Extracts contact information using HTML elements and regular expressions.
4. Detects relevant internal links and adds them to the crawling queue.
5. Identifies external websites associated with accommodation pages.
6. Searches selected pages of those external websites for additional contact information.
7. Stores the collected information.
8. Exports the final results to a CSV file.

## Configuration

The crawler can be configured directly in `scraper.py`.

For example:

```python
MAX_PAGES = 50
CRAWL_DELAY = 0.3
REQUEST_TIMEOUT = 5
MAX_EXTERNAL_PER_PAGE = 3
MAX_WORKERS = 3
```

These options control the maximum number of pages visited, delay between requests, timeout duration, external websites processed per page, and number of worker threads.

## Requirements

The main external dependencies are:

```text
requests
beautifulsoup4
```

Install them using:

```bash
pip install -r requirements.txt
```

## Responsible Use

This project was created for educational purposes and to practice web scraping techniques with Python.

Web scraping should be performed responsibly. Before using the scraper on a website, review the website's terms, crawling policies, and `robots.txt` rules where applicable.

Avoid excessive request rates and unnecessary crawling.

## Learning Objectives

This project demonstrates practical experience with:

- Web scraping
- HTML parsing
- HTTP requests
- URL processing
- Regular expressions
- Data extraction and cleaning
- CSV generation
- Concurrent processing
- Error handling
- Virtual environments
- Git and GitHub

## Author

**Ariadna Pérez Sánchez**

GitHub: `ariadnaperezsanchez`
