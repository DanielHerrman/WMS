# QA Test — B2B Orders + Print3d Regression (2026-07-30)

**URL:** `https://app.lejbl-lab.space/admin/`  
**Login:** `Dinoman95` / `Oid0MOLO95`  

---

## 1. B2B Orders — přejmenování (Custom Orders → B2B Orders)

### 1.1 Sidebar
- [ ] V sidebaru sekce **"3D Printing"** → položka **"B2B Orders"** s ikonkou `business`
- [ ] Kliknutí otevře list view `/admin/print3d/customorder/` — HTTP 200 (ne 404, ne 500)

### 1.2 Breadcrumb a titulky
- [ ] Breadcrumb na list view: **"3D Printing > B2B orders"**
- [ ] Nadpis stránky (h1): **"Select B2B order to change"** (nebo podobné — musí obsahovat "B2B order")
- [ ] Tlačítko "Add" → formulář s nadpisem **"Add B2B order"**
- [ ] Klikni na existující záznam → detail formuláře **"Change B2B order"**

### 1.3 Status field
- [ ] Ve formuláři Add/Change B2B order: **Order Status** dropdown obsahuje:
  - Pending
  - Confirmed
  - **In Production** (NE "Printing"!)
  - Completed
  - Cancelled
- [ ] Vyber **In Production** a ulož. Po uložení se status zobrazuje jako "In Production" (v listu i detailu).

### 1.4 Vytvoření nového B2B order
- [ ] Klikni "Add B2B Order" a vyplň:
  - Project Name: "QA Test Order"
  - Products Count: 5
  - Organization: (vybrat)
  - Printer: (vybrat)
  - Status: **Pending**
  - Filament: (vybrat)
  - Filament Weight: 100
  - Plates Count: 2
  - Print Time: 120
  - Modeling: 30 min / 600 CZK/h
  - Operation: 10 min / 300 CZK/h
  - Postprocessing: 0 min
  - Packaging: 5 min / 250 CZK/h
  - Delivery: Shipping/Courier
  - Shipping Cost: 100
- [ ] Ulož — záznam se vytvoří bez chyby
- [ ] Financial Summary karty se zobrazí správně (Base Cost, +100%, +200%, +350%)
- [ ] Export TXT tlačítko je viditelné a funkční

### 1.5 Status transition → In Production
- [ ] Na existujícím B2B order se statusem **Pending** nebo **Confirmed** změň status na **In Production**
- [ ] Ulož — nesmí spadnout na 500
- [ ] Ověř, že se vytvořil záznam ve **Filament Usage Logs** (sekce 3D Printing > Usage Logs)

---

## 2. Print3d — regression (sekce postižené migrační chybou)

> Tyto stránky vracely 500 po deployi kvůli chybějícím `organization_id` sloupcům. Ověř, že po opravě fungují.

### 2.1 Material Types
- [ ] Otevři `/admin/print3d/materialtype/` — list view bez 500
- [ ] Klikni "Add" — formulář bez 500
- [ ] Vytvoř testovací Material Type: Name "QA Test Material", Organization (vybrat)
- [ ] Ulož — OK

### 2.2 Filament Brands
- [ ] Otevři `/admin/print3d/filamentbrand/` — list view bez 500
- [ ] Klikni "Add" — formulář bez 500
- [ ] Vytvoř testovací Filament Brand: Name "QA Test Brand", Material Type (vybrat), Spool Size 1.0 kg
- [ ] Ulož — OK

### 2.3 Filament Inventory
- [ ] Otevři `/admin/print3d/filament/` — list view bez 500
- [ ] Klikni na existující filament — detail bez 500
- [ ] **Edge:** Status badge se zobrazuje barevně (Ordered = modrá, Stocked = zelená atd.)

### 2.4 Printers
- [ ] Otevři `/admin/print3d/printer/` — list view bez 500
- [ ] Klikni "Add" — formulář bez 500

### 2.5 B2B Orders
- [ ] Otevři `/admin/print3d/customorder/` — list view bez 500
- [ ] Filtry (Organization, Status, Printer, Filament, Delivery Type) fungují
- [ ] Vyhledávání podle Project Name funguje

### 2.6 Usage Logs
- [ ] Otevři `/admin/print3d/filamentusagelog/` — list view bez 500
- [ ] Záznamy jsou readonly (nelze přidat ani editovat)

### 2.7 Step Templates (core — ale chyba se sem šířila)
- [ ] Otevři `/admin/core/productionsteptemplate/` — list view bez 500

---

## 3. Edge Cases

| # | Edge Case | Očekávané chování |
|---|-----------|-------------------|
| 3.1 | B2B Order bez Printer | Uloží se (printer je nullable) |
| 3.2 | B2B Order bez Filament | Uloží se, material cost = 0 |
| 3.3 | Status změna na "In Production" bez filamentu a filament_weight_g=0 | Nesmí spadnout (FilamentUsageLog se nevytvoří) |
| 3.4 | Stará URL `/admin/print3d/customorder/` | Funguje (302 login redirect pokud nejsi přihlášený) |
| 3.5 | B2B Order export TXT (hromadný) | Vybereš v listu záznamy → Action "Export Selected Orders to TXT" → stáhne se .txt soubor |