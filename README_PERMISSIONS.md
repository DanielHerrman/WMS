# Bezpečnostní a Oprávňovací Systém (WMS)

Tento dokument detailně popisuje architekturu oprávnění (Django Groups), automatické přiřazování účtů a bezpečný `Multi-tenant` (systém organizací) návrh pro Unfold Admin a backend.

## 1. Definice skupin a Rozdělení Modelů

Systém pracuje se 3 defualtními skupinami, které jsou nezávislé na Superuserovi (ten má absolutní přístup). 
**Třídění modelů a rolí pro běžné uživatele:**

### 3D Tisk (Role pro Operátory 3D Farem)
Uživatel v této roli drží plná práva pro vytváření, listování, modifikování a mazání dat v doméně 3D tisku:
- `Printer` (Printer Fleet)
- `Filament` (Filament Inventory)
- `CustomOrder` (3D Print Kalkulace)

### Manufacturing (Textil a Print on Cloth)
Přípravná role pro budoucí výrobní moduly (např. potisky textilu).
- *Aktuálně prázdná, připraveno pro napojení dalších sub-modelů z `production`.*

### Základní tarif (Defaultní minimum)
Reprezentuje minimální sadu s pohledovými oprávněními (View) do systému, do které padají noví zákazníci automaticky (více v sekci 2).

---

## 2. Automatické přiřazení (Auto-Provisioning)

Jak systém řeší nově příchozí účty:
- Ve standardním chodu (v souboru `core/models.py`) zachycuje aplikace signál `post_save` z modulu `User`.
- Jakmile je uložen **nový** Uživatel, systém mu automaticky a tiše na pozadí podstrčí skupinu `"Základní tarif"`. 
- Není nutné volat Superusera, aby manuálně zaklikával základní tarif a otevíral mu elementární sekce panelu. Uživatel získá přístup k panelu ihned (dle limitů základní skupiny).
- Pomocí signálu se uživateli též okamžitě definuje prázdný `Profile` záznam, přes který držíme provazbu na `Organization`.

---

## 3. Izolace Organizací (Multi-tenancy Flow)

Každý tenant smí vidět **jen a pouze svá data**, ani neví o existenci ostatních.
- **Skrytí Pole a Falzifikace**: Unfold rozhraní v modelu využívá `MultiTenantAdminMixin`, který metrikou `get_exclude()` natvrdo maže pole `organization` ze všech formulářů (pokud nejsi superuser). Obyčejný člověk prostě nemůže vyplnit "Cizí firmu".
- **Auto-vpis**: V momentě, kdy klikne na "Uložit", metoda `save_model()` na pozadí přiřadí objektu organizaci na základě `request.user.profile.organization`. 
- **Queryset filtrace**: Žádný běžný uživatel nevidí ostatní záznamy, metoda `get_queryset()` do výsledného seznamu propouští jen řádky sdílející stejnou `organization_id`.

---

## 4. Návod: Jak do systému dostat (zaregistrovat) Nové Oprávnění

Pokud v budoucnu tvoříš novou aplikaci a nebo model a chceš jej zavést pod určitou skupinu v Unfold cloudu:
1. **Založení modelu:** Vytvoř model standardně (`models.py`) a napoj ho pomocí ForeignKey na `Organization`, pokud drží data klientů.
2. **Mixin:** Do jeho Admin specifikace (v `admin.py`) přidej hned za `@admin.register(...)` do dědičnosti náš `MultiTenantAdminMixin`.
   *(Poznámka: Nesmí chybět, jinak uvidí data všech)*
3. **Přiřazení do skupiny (UI přes Superusera):** Loguj se jako superuser. Přejdi do "Users & Groups -> Groups". Vyber například skupinu "Manufacturing", scrolluj dolů k seznamu `Permissions`, najdi práva na tvůj nový model a přiřaď je do vybraného boxu.
Nebo zasaď právo rovnou programově do Data Migrace v `core/migrations/0008_create_default_groups.py`.
