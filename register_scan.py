import csv
from datetime import datetime

def registrar_codigo():
    # Importar aquí para evitar error si scanner no existe
    from scanner import scan
    
    codigo = scan()
    
    if not codigo:
        print("❌ No se escaneó código")
        return
    
    with open('mini.csv', 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            codigo
        ])
    
    print(f"✅ Registrado: {codigo}")
    return codigo

if __name__ == "__main__":
    registrar_codigo()