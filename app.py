from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

def normalize_code_from_chz(code):
    """Нормализация кода из системы Честный знак (уже в нужном формате)"""
    code = code.strip()
    # Убираем возможные лишние пробелы
    return code

def normalize_code_from_1c(code):
    """Нормализация кода из 1С: убираем скобки у (01) и (21)"""
    code = code.strip()
    # Убираем скобки у идентификаторов применения
    code = re.sub(r'\(01\)', '01', code)
    code = re.sub(r'\(21\)', '21', code)
    return code

def normalize_code_from_stock(code):
    """Нормализация кода из наличия: удаляем часть начиная с 91"""
    code = code.strip()
    # Находим позицию (91) или 91 и обрезаем всё после
    # В коде маркировки после серийного номера идет (91) - ключ проверки
    match = re.search(r'\(91\)|91', code)
    if match:
        code = code[:match.start()]
    return code

def extract_serial_number(code):
    """Извлекает серийный номер из кода маркировки для сравнения"""
    # Формат: 01<GTIN>21<SERIAL>
    # После нормализации код должен выглядеть как: 0104607049381112215!w4Mw,fE7>SR
    # GTIN всегда 13 цифр после 01, затем 21 и серийный номер
    match = re.match(r'01(\d{13})21(.+)', code)
    if match:
        gtin = match.group(1)
        serial = match.group(2)
        # Для сравнения используем комбинацию GTIN + первые символы серийного номера
        # т.к. в разных системах серийный номер может быть записан по-разному
        return f"{gtin}{serial}"
    return code

def find_codes(chz_codes, sold_codes, stock_codes):
    """Находит потерянные коды маркировки"""
    # Приводим все коды к единому формату и создаем словари для сопоставления
    chz_normalized = {}  # serial -> original_code
    for code in chz_codes:
        normalized = normalize_code_from_chz(code)
        if normalized:
            serial = extract_serial_number(normalized)
            chz_normalized[serial] = normalized
    
    sold_normalized = {}  # serial -> original_code
    for code in sold_codes:
        normalized = normalize_code_from_1c(code)
        if normalized:
            serial = extract_serial_number(normalized)
            sold_normalized[serial] = normalized
    
    stock_normalized = {}  # serial -> original_code
    for code in stock_codes:
        normalized = normalize_code_from_stock(code)
        if normalized:
            serial = extract_serial_number(normalized)
            stock_normalized[serial] = normalized
    
    # Потеряхи = Поступило - Продано - В наличии
    # Сначала находим разницу между поступившими и проданными (по серийным номерам)
    difference_serials = set(chz_normalized.keys()) - set(sold_normalized.keys())
    
    # Затем вычитаем то, что есть в наличии
    lost_serials = difference_serials - set(stock_normalized.keys())
    
    # Возвращаем оригинальные коды из ЧЗ
    lost_codes = [chz_normalized[serial] for serial in lost_serials]
    
    return {
        'chz_count': len(chz_normalized),
        'sold_count': len(sold_normalized),
        'stock_count': len(stock_normalized),
        'difference_count': len(difference_serials),
        'lost_count': len(lost_codes),
        'lost_codes': lost_codes
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/find', methods=['POST'])
def find():
    data = request.get_json()
    
    chz_codes = data.get('chz', '').split('\n')
    sold_codes = data.get('sold', '').split('\n')
    stock_codes = data.get('stock', '').split('\n')
    
    result = find_codes(chz_codes, sold_codes, stock_codes)
    
    return jsonify(result)

@app.route('/normalize', methods=['POST'])
def normalize():
    data = request.get_json()
    
    field = data.get('field')
    codes = data.get('codes', '').split('\n')
    
    normalized = []
    
    if field == 'chz':
        normalized = [normalize_code_from_chz(code) for code in codes]
    elif field == 'sold':
        normalized = [normalize_code_from_1c(code) for code in codes]
    elif field == 'stock':
        normalized = [normalize_code_from_stock(code) for code in codes]
    
    return jsonify({'normalized': '\n'.join(normalized)})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
