import pandas as pd
import re
from typing import List, Dict, Any

# Préfixes pays à normaliser
COUNTRY_PREFIXES = ["224", "232", "44", "001", "1"]

def normalize_phone(raw: str) -> str | None:
    """Supprime les préfixes pays pour obtenir un numéro local canonique."""
    digits = re.sub(r"[^\d]", "", raw)
    if not digits or len(digits) < 7:
        return None
    for prefix in COUNTRY_PREFIXES:
        if digits.startswith(prefix) and len(digits) - len(prefix) >= 7:
            digits = digits[len(prefix):]
            break
    return digits

def is_guinee(phone: str) -> bool:
    """Détecte si un numéro est guinéen."""
    p = re.sub(r"\s", "", phone)
    if p.startswith("224"):
        return True
    if re.match(r"^6\d{7,8}$", p):
        return True
    return False

def parse_excel(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse le fichier Excel YBT et retourne la liste des clients
    avec leurs colis regroupés par numéro de téléphone normalisé.
    """
    df = pd.read_excel(file_path, engine="xlrd", header=None)

    clients: Dict[str, Dict] = {}
    no_phone_idx = 0

    for _, row in df.iterrows():
        seq = row[0]
        if pd.isna(seq) or not str(seq).strip().isdigit():
            continue

        name_raw    = str(row[2]).strip() if not pd.isna(row[2]) else ""
        receipt     = str(row[3]).strip() if not pd.isna(row[3]) else ""
        desc_cn     = str(row[4]).strip() if not pd.isna(row[4]) else ""
        desc_en     = str(row[5]).strip() if not pd.isna(row[5]) else desc_cn
        quantity    = str(row[6]).strip() if not pd.isna(row[6]) else "1"
        cbm_raw     = str(row[7]).strip() if not pd.isna(row[7]) else "0"

        # Nom + téléphones
        parts = re.split(r"[\n\r]+", name_raw)
        display_name = parts[0].strip()
        raw_phones   = re.findall(r"\d{7,}", name_raw)
        norm_phones  = [normalize_phone(p) for p in raw_phones if normalize_phone(p)]
        phone_key    = min(norm_phones, key=len) if norm_phones else None

        if not phone_key:
            no_phone_idx += 1
            phone_key    = f"NOPHONE_{no_phone_idx}_{display_name[:8]}"
            display_phone = ""
        else:
            display_phone = raw_phones[0] if raw_phones else phone_key

        try:
            cbm = float(re.sub(r"[^0-9.]", "", cbm_raw))
        except (ValueError, TypeError):
            cbm = 0.0

        # Création ou mise à jour du client
        if phone_key not in clients:
            clients[phone_key] = {
                "name":       display_name,
                "phone":      display_phone,
                "phone_key":  phone_key,
                "destination": "GN" if is_guinee(display_phone) else "SL",
                "is_merged":  False,
                "items":      [],
            }
        else:
            clients[phone_key]["is_merged"] = True

        clients[phone_key]["items"].append({
            "receipt":     receipt,
            "description": desc_en,
            "quantity":    quantity,
            "cbm":         cbm,
        })

    return list(clients.values())

def compute_amounts(clients: List[Dict], rate_sl: float, rate_gn: float) -> List[Dict]:
    """Calcule freight, custom et total pour chaque client. Sans arrondi."""
    for c in clients:
        rate      = rate_gn if c["destination"] == "GN" else rate_sl
        total_cbm = round(sum(float(i["cbm"]) for i in c["items"]), 10)
        freight   = round((total_cbm * rate) / 2, 10)
        custom    = round((total_cbm * rate) / 2, 10)
        total     = round(total_cbm * rate, 10)
        c.update({
            "total_cbm": total_cbm,
            "freight":   freight,
            "custom":    custom,
            "total_due": total,
            "rate":      rate,
        })
    return clients

def fmt_amount(n: float) -> str:
    """Formate un montant : entier si possible, sinon 2 décimales."""
    return str(int(n)) if n == int(n) else f"{n:.2f}"
