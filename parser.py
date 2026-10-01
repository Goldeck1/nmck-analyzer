import json
import urllib.parse
from datetime import datetime, timedelta
import okpd2
from playwright.sync_api import sync_playwright
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re


def get_publish_date_from():
    """Calculates the date 6 months ago from today."""
    six_months_ago = datetime.now() - timedelta(days=6 * 30)  # Approximation of 6 months
    return six_months_ago.strftime("%d.%m.%Y")


def construct_url(search_string, publish_date_from):
    """Constructs the search URL with parameters."""
    base_url = "https://zakupki.gov.ru/epz/contract/search/results.html"

    params = {
        "searchString": search_string,
        "morphology": "on",
        "fz44": "on",
        "contractStageList_0": "on",
        "contractStageList_1": "on",
        "contractStageList_2": "on",
        "contractStageList_3": "on",
        "contractStageList": "0,1,2,3",
        "selectedContractDataChanges": "ANY",
        "budgetLevelsIdNameHidden": "{}",
        "customerPlaceCodes": 52000000000,
        "publishDateFrom": publish_date_from,
        "countryRegIdNameHidden": "{}",
        "sortBy": "UPDATE_DATE",
        "pageNumber": "1",
        "sortDirection": "false",
        "recordsPerPage": "_10",
        "showLotsInfoHidden": "false"
    }

    return f"{base_url}?{urllib.parse.urlencode(params)}"


def get_ktru_characteristics(page, ktru_url):
    """Visits the KTRU URL and extracts characteristics."""
    print(f"    Processing KTRU: {ktru_url}")
    try:
        page.goto(ktru_url, timeout=60000)
        page.wait_for_selector(".blockInfo__section", timeout=30000)

        characteristics = {}
        sections = page.query_selector_all(".blockInfo__section")

        for section in sections:
            title_el = section.query_selector(".section__title")
            info_el = section.query_selector(".section__info")

            if title_el and info_el:
                title = title_el.inner_text().strip()
                # Skip the header title "Характеристики позиции КТРУ" if it appears as a section title
                if "Характеристики позиции КТРУ" in title:
                    continue

                info = info_el.inner_text().strip()
                characteristics[title] = info

        return characteristics
    except Exception as e:
        print(f"    Error processing KTRU {ktru_url}: {e}")
        return {}


def get_ktru_links(page, contract_url, search_term):
    """Visits the contract URL and extracts KTRU characteristic links, object name and price."""
    print(f"Processing {contract_url}")
    try:
        page.goto(contract_url, timeout=60000)
        # Wait for some element that indicates page load, or just body
        page.wait_for_selector("body", timeout=30000)

        # Extract contract-level information first
        contract_info = {
            "registry_number": "",
            "customer_name": "",
            "total_contract_price": "",
            "contract_date": "",
            "execution_deadline": "",
            "registry_placement_date": ""
        }
        
        # Extract registry number
        try:
            registry_link = page.query_selector(".cardMainInfo__purchaseLink a")
            if registry_link:
                registry_text = registry_link.inner_text().strip()
                contract_info["registry_number"] = registry_text.replace("№", "").strip()
        except:
            pass
        
        # Extract customer name
        try:
            sections = page.query_selector_all(".cardMainInfo__section")
            for section in sections:
                title_el = section.query_selector(".cardMainInfo__title")
                if title_el and "Заказчик" in title_el.inner_text():
                    content_el = section.query_selector(".cardMainInfo__content")
                    if content_el:
                        # Get text from link if present, otherwise from content
                        link_el = content_el.query_selector("a")
                        if link_el:
                            contract_info["customer_name"] = link_el.inner_text().strip()
                        else:
                            contract_info["customer_name"] = content_el.inner_text().strip()
                    break
        except:
            pass
        
        # Extract total contract price
        try:
            price_el = page.query_selector(".price .cardMainInfo__content.cost")
            if price_el:
                contract_info["total_contract_price"] = price_el.inner_text().strip()
        except:
            pass
        
        # Extract dates - search all cardMainInfo__section elements
        try:
            all_sections = page.query_selector_all(".cardMainInfo__section")
            for section in all_sections:
                title_el = section.query_selector(".cardMainInfo__title")
                content_el = section.query_selector(".cardMainInfo__content")
                if title_el and content_el:
                    title_text = title_el.inner_text().strip()
                    content_text = content_el.inner_text().strip()
                    
                    if "Заключение контракта" in title_text:
                        contract_info["contract_date"] = content_text
                    elif "Срок исполнения" in title_text:
                        contract_info["execution_deadline"] = content_text
                    elif "Размещен контракт в реестре контрактов" in title_text:
                        contract_info["registry_placement_date"] = content_text
        except:
            pass

        # Wait for the contract subjects table, but don't fail if it's not there (empty subjects?)
        try:
            page.wait_for_selector("#contract_subjects", timeout=10000)
        except:
            print(f"  No contract subjects table found on {contract_url}")
            return []

        data_list = []
        # Select all rows in the table body
        rows = page.query_selector_all("#contract_subjects tbody tr.tableBlock__row")

        for row in rows:
            # The structure based on solo.html:
            # td 1: empty or count
            # td 2: Name and KTRU link. Name is in .padBtm5

            # Find the object name element
            name_element = row.query_selector(".padBtm5")
            if not name_element:
                continue

            object_name_text = name_element.inner_text().strip()
            # Remove item number from the beginning if present (e.g., "1. " or "1.")
            object_name_text = re.sub(r'^\d+\.\s*', '', object_name_text).strip()

            # Check if search_term is in the object name (case-insensitive)
            # Look for KTRU link in this row (it's usually in the same cell or nearby)
            # Based on solo.html, the link is in the same cell (td 2) inside a div with class grey-main-light
            link_element = row.query_selector('a[href*="ktru-characteristics.html"]')

            ktru_link = None
            if link_element:
                href = link_element.get_attribute("href")
                if href:
                    ktru_link = f"https://zakupki.gov.ru{href}"

            # Extract price (td 6)
            # Based on solo.html: <td class="tableBlock__col tableBlock__col_right"> 37 800,00 </td>
            # Note: indices in query_selector_all are 0-based.
            # td 1: index 0
            # td 2: index 1 (Name & KTRU)
            # td 3: index 2 (Code - KTRU/OKPD2)
            # td 4: index 3 (Type)
            # td 5: index 4 (Quantity)
            # td 6: index 5 (Price per unit)
            # td 7: index 6 (Total Sum)
            
            cells = row.query_selector_all("td")
            
            # Extract KTRU/OKPD2 Code (td 3)
            ktru_code = "N/A"
            if len(cells) > 2:
                ktru_code = cells[2].inner_text().strip()
                
            # Extract Quantity (td 5)
            quantity = "N/A"
            if len(cells) > 4:
                quantity = cells[4].inner_text().strip()

            # Extract Price per Unit (td 6)
            price_per_unit = "N/A"
            if len(cells) > 5:
                price_per_unit = cells[5].inner_text().strip()
                
            # Extract Total Sum (td 7)
            total_sum = "N/A"
            if len(cells) > 6:
                total_sum = cells[6].inner_text().strip()

            # Collect data even if KTRU link is missing (requested feature)
            ktru_link_str = ktru_link if ktru_link else "N/A"
            
            # Only add if the link is present OR if we want all items matching search term even without links
            # The prompt implies we want to collect items matching search term, and if ktru link exists, get characteristics.
            # "А также обработку ситуаций когда ссылок на характеристики нет" -> implies we should collect item even if no link.
            
            data_list.append({
                "name": object_name_text,
                "ktru_code": ktru_code,
                "quantity": quantity,
                "price": price_per_unit,
                "total_sum": total_sum,
                "ktru_link": ktru_link_str,
                "registry_number": contract_info["registry_number"],
                "customer_name": contract_info["customer_name"],
                "total_contract_price": contract_info["total_contract_price"],
                "contract_date": contract_info["contract_date"],
                "execution_deadline": contract_info["execution_deadline"],
                "registry_placement_date": contract_info["registry_placement_date"]
            })

        return data_list
    except Exception as e:
        print(f"Error processing {contract_url}: {e}")
        return []


def parse_zakupki(search_string):
    """Parses zakupki.gov.ru for contract information and extracts KTRU links."""
    publish_date_from = get_publish_date_from()
    target_url = construct_url(search_string, publish_date_from)

    print(f"Navigating to search results: {target_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Step 1: Get list of contracts
            page.goto(target_url, timeout=60000)
            page.wait_for_selector(".search-registry-entry-block", timeout=30000)

            entries = page.query_selector_all(".search-registry-entry-block")

            contract_urls = []
            for entry in entries:
                number_link = entry.query_selector(".registry-entry__header-mid__number a")
                if number_link:
                    reestr_number = number_link.inner_text().strip()
                    reestr_number = reestr_number.replace("№", "").strip()
                    payment_info_url = f"https://zakupki.gov.ru/epz/contract/contractCard/payment-info-and-target-of-order.html?reestrNumber={reestr_number}#contractSubjects"
                    contract_urls.append(payment_info_url)

            print(f"Found {len(contract_urls)} contracts. Starting extraction of KTRU links...")

            # Step 2: Visit each contract and extract items
            results = {}
            for url in contract_urls:
                extracted_data = get_ktru_links(page, url, search_string)
                
                if extracted_data:
                    # Step 3: For each extracted item with a KTRU link, visit and get characteristics
                    for item in extracted_data:
                        if item['ktru_link'] != "N/A":
                            characteristics = get_ktru_characteristics(page, item['ktru_link'])
                            item['characteristics'] = characteristics
                        else:
                            item['characteristics'] = {"Info": "No KTRU link available"}
                    
                    results[url] = extracted_data
                    print(f"  Found {len(extracted_data)} matching items for {url}")
                else:
                    print(f"  No matching items found for {url}")

            return results

        except Exception as e:
            print(f"An error occurred: {e}")
            return {}
        finally:
            browser.close()


def parse_price(price_str):
    """Extract numeric price value from string."""
    if not price_str or price_str == "N/A":
        return None
    # Remove all non-digit characters except comma and dot
    cleaned = re.sub(r'[^\d,.]', '', price_str.replace('\xa0', '').replace(' ', ''))
    # Replace comma with dot for decimal
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return None

def calculate_median(prices):
    """Calculate median of prices."""
    if not prices:
        return None
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    if n % 2 == 0:
        return (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
    else:
        return sorted_prices[n//2]

def find_closest_to_median(data, median_price):
    """Find 3 contracts with prices closest to median."""
    if not median_price:
        return []
    
    # Add price difference to each item
    items_with_diff = []
    for item in data:
        price = parse_price(item.get('price', ''))
        if price is not None:
            diff = abs(price - median_price)
            items_with_diff.append((diff, item, price))
    
    # Sort by difference and take top 3
    items_with_diff.sort(key=lambda x: x[0])
    return [(item, price) for _, item, price in items_with_diff[:3]]

def add_hyperlink_to_paragraph(paragraph, text, url):
    """Add a hyperlink to a paragraph."""
    from docx.oxml import parse_xml
    
    part = paragraph.part
    
    # Add relationship for hyperlink
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    
    # Create hyperlink XML
    hyperlink_xml = f'<w:hyperlink r:id="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    hyperlink = parse_xml(hyperlink_xml)
    
    # Add run with text
    run = paragraph.add_run(text)
    run.font.color.rgb = None  # Use default color (blue for hyperlinks)
    run.font.underline = True
    
    # Move run into hyperlink
    run._element.getparent().remove(run._element)
    hyperlink.append(run._element)
    
    # Add hyperlink to paragraph
    paragraph._p.append(hyperlink)

def generate_report(data, search_term, okpd2_codes, good_quantity=None, good_description=None):
    """Generate Word document report based on parsed data."""
    # Extract prices and calculate median
    prices = []
    for item in data:
        price = parse_price(item.get('price', ''))
        if price is not None:
            prices.append(price)
    
    if not prices:
        print("No valid prices found for report generation.")
        return
    
    median_price = calculate_median(prices)
    closest_items = find_closest_to_median(data, median_price)
    
    if len(closest_items) < 3:
        print(f"Only {len(closest_items)} items with valid prices found. Need at least 3 for report.")
        return
    
    # Initialize nmck variable
    nmck = None
    
    # Create document
    doc = Document()
    
    # Title
    title = doc.add_heading('ОБОСНОВАНИЕ НАЧАЛЬНОЙ (МАКСИМАЛЬНОЙ) ЦЕНЫ КОНТРАКТА (НМЦК)', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Section 1: ПРЕДМЕТ ЗАКУПКИ
    doc.add_heading('1. ПРЕДМЕТ ЗАКУПКИ', level=1)
    doc.add_paragraph(f'Наименование: {search_term}')
    description_text = good_description if good_description else '[Заполнить самостоятельно]'
    doc.add_paragraph(f'Краткое описание: {description_text}')
    quantity_text = str(good_quantity) if good_quantity else '[Заполнить самостоятельно]'
    doc.add_paragraph(f'Количество: {quantity_text}')
    
    # Section 2: РАСЧЕТ И ОБОСНОВАНИЕ НМЦК
    doc.add_heading('2. РАСЧЕТ И ОБОСНОВАНИЕ НМЦК', level=1)
    
    # Subsection 2.1
    doc.add_heading('2.1. Анализ информации, размещенной в ЕИС', level=2)
    doc.add_paragraph('В целях определения рыночного уровня цен проведен анализ сведений из реестра контрактов на официальном сайте www.zakupki.gov.ru.')
    doc.add_paragraph('Критерии поиска:')
    
    # OKPD2 codes
    okpd2_text = ', '.join(okpd2_codes) if okpd2_codes else '[Коды не найдены]'
    doc.add_paragraph(f'Код КТРУ/ОКПД2: {okpd2_text}')
    
    publish_date_from = get_publish_date_from()
    doc.add_paragraph(f'Период размещения извещений: последние 6 месяцев (с {publish_date_from} по {datetime.now().strftime("%d.%m.%Y")}).')
    doc.add_paragraph('Статус закупки: Закупка завершена, контракт заключен.')
    
    doc.add_paragraph(f'В результате анализа отобраны три контракта, являющиеся аналогами предмета закупки. Данные по ним приведены в таблице 1.')
    
    # Table
    doc.add_paragraph('Таблица 1. Анализ контрактов-аналогов из реестра контрактов ЕИС')
    
    table = doc.add_table(rows=1, cols=8)
    table.style = 'Light Grid Accent 1'
    
    # Header row
    header_cells = table.rows[0].cells
    headers = ['№ п/п', 'Реестровый номер контракта, дата заключения', 'Наименование заказчика', 
               'Предмет контракта', 'Ключевые характеристики объекта закупки', 
               'Количество, ед. изм.', 'Цена за ед., руб. (без НДС)', 'Общая цена контракта, руб. (без НДС)']
    
    for i, header in enumerate(headers):
        header_cells[i].text = header
        for paragraph in header_cells[i].paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)
    
    # Data rows
    for idx, (item, price) in enumerate(closest_items, 1):
        row_cells = table.add_row().cells
        row_cells[0].text = str(idx)
        
        # Registry number with link
        registry_num = item.get('registry_number', '')
        contract_date = item.get('contract_date', '')
        contract_url = item.get('contract_url', '')
        registry_text = f"№ {registry_num} от {contract_date}" if registry_num and contract_date else f"№ {registry_num}" if registry_num else "N/A"
        
        # Add contract URL to the cell with hyperlink
        paragraph = row_cells[1].paragraphs[0]
        paragraph.clear()
        paragraph.add_run(registry_text)
        if contract_url:
            paragraph.add_run('\n')
            add_hyperlink_to_paragraph(paragraph, "Ссылка на контракт", contract_url)
        else:
            row_cells[1].text = registry_text
        
        row_cells[2].text = item.get('customer_name', 'N/A')
        row_cells[3].text = item.get('text', 'N/A')
        row_cells[4].text = item.get('characteristic', 'N/A')[:200] + '...' if len(item.get('characteristic', '')) > 200 else item.get('characteristic', 'N/A')
        row_cells[5].text = item.get('quantity', 'N/A')
        row_cells[6].text = f"{price:,.2f}".replace(',', ' ')
        total_sum = parse_price(item.get('total_sum', ''))
        if total_sum:
            row_cells[7].text = f"{total_sum:,.2f}".replace(',', ' ')
        else:
            row_cells[7].text = item.get('total_sum', 'N/A')
        
        # Set font size for all cells
        for cell in row_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
    
    doc.add_paragraph('Источник данных: Официальный сайт ЕИС (zakupki.gov.ru).')
    
    # Subsection 2.2
    doc.add_heading('2.2. Расчет НМЦК', level=2)
    doc.add_paragraph('Расчет произведен на основании цен за единицу измерения, указанных в отобранных контрактах-аналогах.')
    
    for idx, (item, price) in enumerate(closest_items, 1):
        registry_num = item.get('registry_number', '')
        doc.add_paragraph(f'Цена за единицу по контракту № {registry_num}: {price:,.2f} руб.'.replace(',', ' '))
    
    # Calculate average
    avg_price = sum(price for _, price in closest_items) / len(closest_items)
    doc.add_paragraph('Расчет средней цены за единицу:')
    # Format prices with spaces: "(43 614.00 +  41 601.07 +  41 340.00)"
    price_list = ' +  '.join([f"{price:,.2f}".replace(',', ' ') for _, price in closest_items])
    doc.add_paragraph(f'({price_list}) / {len(closest_items)} = {avg_price:,.2f} руб. за единицу.'.replace(',', ' '))
    
    doc.add_paragraph('Расчет итоговой НМЦК:')
    if good_quantity:
        nmck = avg_price * good_quantity
        doc.add_paragraph(f'{avg_price:,.2f} руб./ед. * {good_quantity} ед. = {nmck:,.2f} руб.'.replace(',', ' '))
    else:
        doc.add_paragraph(f'{avg_price:,.2f} руб./ед. * [количество] ед. = [НМЦК] руб.'.replace(',', ' '))
        nmck = None
    
    # Section 3: ИТОГОВОЕ РЕШЕНИЕ
    doc.add_heading('3. ИТОГОВОЕ РЕШЕНИЕ', level=1)
    if nmck is not None:
        doc.add_paragraph(f'Итоговая НМЦК: {nmck:,.2f} рублей.'.replace(',', ' '))
    else:
        doc.add_paragraph('Итоговая НМЦК: [НМЦК] рублей.')
    doc.add_paragraph('')
    doc.add_paragraph(datetime.now().strftime("%d.%m.%Y"))
    
    # Save document
    filename = f'report_{search_term.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx'
    doc.save(filename)
    print(f"\nReport saved as: {filename}")


if __name__ == "__main__":
    # Example usage
    API_KEY = os.getenv("OKPD2_API_KEY", "")
    if not API_KEY:
        raise RuntimeError("Set OKPD2_API_KEY before running this example")
    search_term = "ноутбук"
    good_quantity = 15
    good_description = "Ноутбук с 8gb ram"
    data = parse_zakupki(search_term)
    okpd2_codes = okpd2.get_okpd2_codes(search_term, API_KEY)
    print("\nExtraction Complete. Results:")
    formatted_data = []
    for contract, items in data.items():
        #print(f"\nContract: {contract}")
        for item in items:
            chars = ""
            print(f"  - Name: {item['name']}")
            print(f"    Code: {item['ktru_code']}")
            print(f"    Qty: {item['quantity']}")
            print(f"    Price: {item['price']}")
            print(f"    Total: {item['total_sum']}")
            print(f"    Registry Number: {item.get('registry_number', 'N/A')}")
            print(f"    Customer: {item.get('customer_name', 'N/A')}")
            print(f"    Total Contract Price: {item.get('total_contract_price', 'N/A')}")
            print(f"    Contract Date: {item.get('contract_date', 'N/A')}")
            print(f"    Execution Deadline: {item.get('execution_deadline', 'N/A')}")
            print(f"    Registry Placement Date: {item.get('registry_placement_date', 'N/A')}")
            print(f"    KTRU Link: {item['ktru_link']}")
            print(f"    Characteristics:")
            for k, v in item.get('characteristics', {}).items():
                if k == "Info" and v == "No KTRU link available":
                    chars = ""
                    break
                chars += f"{k}: {v}; "
                print(f"      {k}: {v}")
            formatted_data.append({
                "text": item['name'],
                "ktru_code": item['ktru_code'],
                "quantity": item['quantity'],
                "price": item['price'],
                "total_sum": item['total_sum'],
                "characteristic": chars,
                "contract_url": contract,
                "registry_number": item.get('registry_number', ''),
                "customer_name": item.get('customer_name', ''),
                "total_contract_price": item.get('total_contract_price', ''),
                "contract_date": item.get('contract_date', ''),
                "execution_deadline": item.get('execution_deadline', ''),
                "registry_placement_date": item.get('registry_placement_date', '')
            })
    print(formatted_data)
    ourjson = {
        "data": formatted_data,
        "okpd2_codes": okpd2_codes
    }
    with open('data.json', 'w') as f:
        json.dump(ourjson, f,indent=4)
        #print(json.dumps(formatted_data,indent=4))
    
    # Generate report
    generate_report(formatted_data, search_term, okpd2_codes, good_quantity, good_description)


