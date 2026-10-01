"""
Модуль для генерации отчетов в формате Word.
"""
import io
from datetime import datetime
from typing import List, Dict, Optional
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml

from parser import (
    get_publish_date_from,
    parse_price
)


def add_hyperlink_to_paragraph(paragraph, text, url):
    """Add a hyperlink to a paragraph."""
    part = paragraph.part
    
    # Add relationship for hyperlink
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    
    # Create hyperlink XML
    hyperlink_xml = f'<w:hyperlink r:id="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    hyperlink = parse_xml(hyperlink_xml)
    
    # Add run with text
    run = paragraph.add_run(text)
    run.font.color.rgb = None
    run.font.underline = True
    
    # Move run into hyperlink
    run._element.getparent().remove(run._element)
    hyperlink.append(run._element)
    
    # Add hyperlink to paragraph
    paragraph._p.append(hyperlink)


def generate_report_from_approved(
    approved_items: List[Dict],
    search_term: str,
    okpd2_codes: List[str],
    good_quantity: Optional[int] = None,
    good_description: Optional[str] = None
) -> io.BytesIO:
    """
    Генерирует отчет Word из одобренных товаров.
    
    Args:
        approved_items: Список одобренных товаров
        search_term: Название товара для поиска
        okpd2_codes: Список кодов ОКПД2
        good_quantity: Количество товара
        good_description: Описание товара
        
    Returns:
        BytesIO объект с содержимым docx файла
    """
    if not approved_items:
        raise ValueError("Нет одобренных товаров для генерации отчета")
    
    # Берем первые 3 элемента из approved_items с валидными ценами
    closest_items = []
    for item in approved_items:
        price = parse_price(item.get('price', ''))
        if price is not None:
            closest_items.append((item, price))
            if len(closest_items) >= 3:
                break
    
    if not closest_items:
        raise ValueError("Не удалось найти товары с валидными ценами")
    
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
    doc.add_paragraph(f'Количество, ед. изм. {quantity_text}')
    
    # Section 2: РАСЧЕТ НМЦК
    doc.add_heading('2. РАСЧЕТ НМЦК', level=1)
    
    # Subsection 2.1: Расчет НМЦК
    doc.add_heading('2.1. Расчет НМЦК', level=2)
    doc.add_paragraph('Расчет произведен на основании цен за единицу измерения, указанных в отобранных контрактах-аналогах.')
    
    # Calculate average first (needed for later)
    avg_price = sum(price for _, price in closest_items) / len(closest_items)
    
    # Add price per unit for each item with hyperlink to contract
    for item, price in closest_items:
        item_name = item.get('text', 'N/A')
        contract_url = item.get('contract_url', '')
        
        # Create paragraph with hyperlink in item name
        para = doc.add_paragraph()
        para.add_run('Цена за единицу товара ')
        
        # Add item name as hyperlink if contract_url exists
        if contract_url:
            add_hyperlink_to_paragraph(para, item_name, contract_url)
        else:
            para.add_run(item_name)
        
        para.add_run(f' : {price:,.2f} руб.'.replace(',', ' '))
    
    # Calculate average
    doc.add_paragraph('Расчет средней цены за единицу:')
    price_list = ' +  '.join([f"{price:,.2f}".replace(',', ' ') for _, price in closest_items])
    doc.add_paragraph(f'({price_list}) / {len(closest_items)} = {avg_price:,.2f} руб. за единицу.'.replace(',', ' '))
    
    doc.add_paragraph('Расчет итоговой НМЦК:')
    if good_quantity:
        nmck = avg_price * good_quantity
        doc.add_paragraph(f'{avg_price:,.2f} руб./ед. * {good_quantity} ед. = {nmck:,.2f} руб.'.replace(',', ' '))
    else:
        doc.add_paragraph(f'{avg_price:,.2f} руб./ед. * [количество] ед. = [НМЦК] руб.'.replace(',', ' '))
        nmck = None
    
    # Subsection 2.2: ИТОГОВОЕ РЕШЕНИЕ
    doc.add_heading('2.2 ИТОГОВОЕ РЕШЕНИЕ', level=2)
    if nmck is not None:
        doc.add_paragraph(f'Итоговая НМЦК: {nmck:,.2f} рублей.'.replace(',', ' '))
    else:
        doc.add_paragraph('Итоговая НМЦК: [НМЦК] рублей.')
    doc.add_paragraph('')
    
    # Section 3: Обоснование
    doc.add_heading('3. Обоснование', level=1)
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
        
        # Registry number (without hyperlink)
        registry_num = item.get('registry_number', '')
        contract_date = item.get('contract_date', '')
        registry_text = f"№ {registry_num} от {contract_date}" if registry_num and contract_date else f"№ {registry_num}" if registry_num else "N/A"
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
    
    doc.add_paragraph('')
    doc.add_paragraph(datetime.now().strftime("%d.%m.%Y"))
    
    # Save to BytesIO
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output, nmck, avg_price

