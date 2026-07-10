from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.append(['name', 'description', 'quantity', 'category'])
ws.append(['Arduino Uno', 'Mikrodenetleyici kartı', 10, 'Elektronik'])
ws.append(['Raspberry Pi', 'Tek kartlı bilgisayar', 5, 'Bilgisayar'])
ws.append(['Servo Motor', 'Döner motor', 20, 'Motor'])
ws.append(['LED', 'Işık yayan diyot', 100, 'Işık'])
ws.append(['Breadboard', 'Devre tahtası', 15, 'Araç'])
wb.save('inventory.xlsx')
print("Örnek inventory.xlsx oluşturuldu.")