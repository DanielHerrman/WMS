# QA Prompt — Fáze 2: Výrobní logika (verifikace na produkci)

**Aplikace:** Django + Unfold admin na https://app.lejbl-lab.space
**Login:** Dinoman95 / Oid0MOLO95
**Organizace:** Bracon

---

## Předpoklady — ověř před testováním

1. **Produkt B2B-CUSTOM existuje:**
   - Jdi do **Core → Products**
   - Hledej SKU `B2B-CUSTOM`
   - ✅ Musí existovat, name = "B2B Custom Manufacturing", Organization = Bracon, is_purchased = False

2. **ProductionStepTemplate šablony existují (5 univerzálních pro Bracon):**
   - Jdi do **Core → Production Step Templates**
   - Filtruj Organization = Bracon
   - ✅ Musíš vidět 5 kroků:
     - #1 Příprava tiskárny (product=None, material_type=None)
     - #2 3D tisk (product=None, material_type=None)
     - #3 Odebrání z podložky (product=None, material_type=None)
     - #4 Kontrola kvality (product=None, material_type=None)
     - #5 Balení a expedice (product=None, material_type=None)
   - 📝 Pokud některý chybí, vytvoř ho ručně (přes "Add Production Step Template")

3. **Printer existuje:**
   - Jdi do **Print3d → Printer Fleet**
   - ✅ Alespoň 1 printer s Organization = Bracon

4. **Filament existuje:**
   - Jdi do **Print3d → Filament Inventory**
   - ✅ Alespoň 1 filament se statusem "Stocked" nebo "In Use"

---

## Test 1: B2B Order Confirmed → auto-generuje ProductionOrder

**Kroky:**
1. Jdi do **Print3d → B2B orders**
2. Klikni **"Add B2B order"** (nebo edituj existující Pending order)
3. Vyplň:
   - Organization: **Bracon**
   - Project Name: **QA Test Fáze 2**
   - Products Count: **3**
   - Status: **Pending** (zatím!)
   - Printer: vyber existující
   - Filament: vyber existující
   - Filament Weight: **200**
   - Ostatní: default
4. **Save**
5. **Znovu edituj** → změň Status na **Confirmed** → **Save**

**Ověření:**
- Jdi do **Core → Production Orders**
- ✅ Musíš vidět nový Production Order s:
  - Product = **B2B-CUSTOM**
  - Quantity = **3**
  - Status = **Queued**
  - Custom Order = QA Test Fáze 2
  - 5 kroků (viz inline Steps)
- Přejdi zpět do B2B orders → otevři "QA Test Fáze 2" → znovu Save (beze změny)
- ✅ V Core → Production Orders musí být stále jen **1** PO pro tuto objednávku (žádný duplikát!)

---

## Test 2: ProductionOrderAdmin zobrazuje Assigned Filament

**Kroky:**
1. Jdi do **Core → Production Orders**
2. Otevři PO vytvořený v Testu 1

**Ověření:**
- ✅ V list_display (tabulkový přehled) je sloupec **"Assigned Filament"**
- ✅ Ve formuláři (sekce Assignment) je pole **"Assigned filament"** (autocomplete na Filament)
- Přiřaď filament: vyber cívku z Testu 1 → **Save**
- ✅ Po uložení se filament zobrazuje v list_display

---

## Test 3: Dokončení kroku "3D tisk" → odepíše filament do UsageLog

**Kroky:**
1. Jdi do **Core → Production Orders** → otevři PO z Testu 1
2. Ověř, že má přiřazený filament (Test 2)
3. Scrollni dolů do **Production Steps** inline tabulky
4. Klikni na řádek **"3D tisk"** (step_number=2) — otevře se editace kroku
5. Zaškrtni **"Is completed"** → **Save** (completed_by a completed_at by se měly vyplnit automaticky, pokud ne, nastav ručně)

**Ověření:**
- Jdi do **Print3d → Filament Usage Logs**
- ✅ Musíš vidět nový záznam:
  - Filament = přiřazená cívka
  - Custom Order = QA Test Fáze 2
  - Grams Used = **200.00** (hodnota z filament_weight_g B2B objednávky)

---

## Test 4: Edge case — B2B Order bez printeru

**Kroky:**
1. Vytvoř nový B2B Order:
   - Project Name: **QA Test No Printer**
   - Products Count: 1
   - Status: Pending
   - Printer: **nechat prázdné**
   - Filament: vyber
   - Filament Weight: 50
2. Save → změň na Confirmed → Save

**Ověření:**
- ✅ Production Order se vytvořil (Product = B2B-CUSTOM)
- ✅ assigned_printer = None (prázdné)
- ✅ Steps se naklonovaly
- ✅ Žádná error hláška / 500

---

## Test 5: Edge case — dokončení 3D tisk bez přiřazeného filamentu

**Kroky:**
1. V PO z Testu 4 (nebo jiném) **odeber přiřazený filament** (smaž hodnotu v assigned_filament → Save)
2. Dokonči krok "3D tisk" (zaškrtni is_completed → Save)

**Ověření:**
- ✅ Krok se úspěšně dokončil
- ✅ **Žádný nový FilamentUsageLog** (protože filament nebyl přiřazen)
- ✅ Žádná 500 / error

---

## Souhrn — checklist

- [ ] B2B-CUSTOM produkt existuje (SKU: B2B-CUSTOM)
- [ ] 5 univerzálních ProductionStepTemplate existuje pro Bracon
- [ ] B2B Order Confirmed → ProductionOrder vytvořen s 5 kroky
- [ ] PO má custom_order vazbu na zdrojový B2B Order
- [ ] Opakované uložení B2B Order nevytváří duplicitní PO
- [ ] ProductionOrderAdmin list_display obsahuje "Assigned Filament"
- [ ] Lze přiřadit filament k PO přes admin
- [ ] Dokončení kroku "3D tisk" vytvoří FilamentUsageLog se správnou gramáží
- [ ] B2B Order bez printeru → PO se vytvoří, assigned_printer = None
- [ ] Dokončení "3D tisk" bez assigned_filament → nespadne, UsageLog se nevytvoří
- [ ] Nikde žádná 500 / Internal Server Error