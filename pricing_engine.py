"""Server-side prijsengine voor de configurators."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class QuoteResult:
  """Gestandaardiseerde representatie van een offerteberekening."""

  total: float
  breakdown: List[Dict[str, float]] = field(default_factory=list)
  message: str | None = None

  def to_dict(self) -> Dict[str, Any]:
    data: Dict[str, Any] = {"total": round(self.total, 2)}
    if self.breakdown:
      data["breakdown"] = [
        {"label": item["label"], "amount": round(float(item["amount"]), 2)}
        for item in self.breakdown
      ]
    if self.message:
      data["message"] = self.message
    return data


def _to_float(value: Any, default: float = 0.0) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return default


def _to_positive(value: float) -> float:
  return max(0.0, value)


def _append_breakdown(items: List[Dict[str, float]], label: str, amount: float) -> None:
  if abs(amount) < 0.01:
    return
  items.append({"label": label, "amount": amount})


def calculate_uitbouw(payload: Dict[str, Any]) -> QuoteResult:
  width = _to_positive(_to_float(payload.get("breedte")))
  depth = _to_positive(_to_float(payload.get("diepte")))
  area = width * depth
  total = area * 2100
  breakdown: List[Dict[str, float]] = []
  _append_breakdown(breakdown, "Basisconstructie", area * 2100)

  if payload.get("daktype") == "schuin":
    extra = area * 200
    total += extra
    _append_breakdown(breakdown, "Schuindak", extra)

  daglicht_pricing = {
    "koepel": 750,
    "daklicht": 1100,
    "lichtstraat_smal": 1950,
    "lichtstraat_breed": 2650,
  }
  daglicht_choice = payload.get("daglicht")
  daglicht_amount = daglicht_pricing.get(daglicht_choice, 0)
  total += daglicht_amount
  _append_breakdown(breakdown, "Daglicht", daglicht_amount)

  pui_pricing = {
    "hefschuif2": 4900,
    "hefschuif3": 6400,
    "kiepschuif": 4500,
    "vouwwand": 6100,
  }
  pui_amount = pui_pricing.get(payload.get("pui"), 0)
  total += pui_amount
  _append_breakdown(breakdown, "Gevelpui", pui_amount)

  if payload.get("glas") == "triple":
    triple_amount = area * 85
    total += triple_amount
    _append_breakdown(breakdown, "Triple glas", triple_amount)

  if payload.get("vloerverwarming") == "ja":
    vloerverwarming = area * 55
    total += vloerverwarming
    _append_breakdown(breakdown, "Vloerverwarming", vloerverwarming)

  stuc_rate = 25 if payload.get("stuc") == "spachtelputz" else 18
  stuc_amount = area * stuc_rate
  total += stuc_amount
  _append_breakdown(breakdown, "Binnenafwerking", stuc_amount)

  region_factor = 1.1 if str(payload.get("postcode", "")).strip().upper().startswith("1") else 1.0
  message = None
  if region_factor != 1.0:
    total *= region_factor
    message = f"Regionale factor {region_factor:.2f} toegepast op basis van postcode."

  return QuoteResult(total=total, breakdown=breakdown, message=message)


def calculate_dakkapel(payload: Dict[str, Any]) -> QuoteResult:
  meters = _to_positive(_to_float(payload.get("breedte")))
  total = meters * 1450
  breakdown: List[Dict[str, float]] = []
  _append_breakdown(breakdown, "Prefab basis", total)

  if payload.get("hoogte") == "verhoogd":
    verhoogd = meters * 350
    total += verhoogd
    _append_breakdown(breakdown, "Verhoogde kap", verhoogd)

  indeling_costs = {"2vakken": 150, "3vakken": 300, "4vakken": 450}
  indeling_amount = indeling_costs.get(payload.get("indeling"), 0)
  total += indeling_amount
  _append_breakdown(breakdown, "Indeling", indeling_amount)

  if payload.get("glas") == "triple":
    triple = meters * 250
    total += triple
    _append_breakdown(breakdown, "Triple glas", triple)

  if payload.get("roosters") == "pervak":
    roosters = meters * 90
    total += roosters
    _append_breakdown(breakdown, "Ventilatieroosters", roosters)

  if payload.get("horren") == "draaikiep":
    horren = meters * 110
    total += horren
    _append_breakdown(breakdown, "Horren", horren)

  if payload.get("zonwering") == "screens":
    screens = meters * 325
    total += screens
    _append_breakdown(breakdown, "Screens", screens)
  elif payload.get("zonwering") == "rolluiken":
    rolluiken = meters * 525
    total += rolluiken
    _append_breakdown(breakdown, "Rolluiken", rolluiken)

  if payload.get("kleur") == "houtnerf":
    houtnerf = total * 0.1
    total += houtnerf
    _append_breakdown(breakdown, "Houtnerf folie", houtnerf)

  region_factor = 1.05 if str(payload.get("postcode", "")).strip().upper().startswith("2") else 1.0
  message = None
  if region_factor != 1.0:
    total *= region_factor
    message = "Regiofactor 1.05 toegepast (Randstad)."

  return QuoteResult(total=total, breakdown=breakdown, message=message)


def calculate_stuc(payload: Dict[str, Any]) -> QuoteResult:
  binnen = _to_positive(_to_float(payload.get("m2Binnen")))
  buiten = _to_positive(_to_float(payload.get("m2Buiten")))
  breakdown: List[Dict[str, float]] = []
  stuc_tarief = {"sausklaar": 18, "spachtelputz": 25, "schuurwerk": 22}
  binnen_afwerking = binnen * stuc_tarief.get(payload.get("afwerkingBinnen"), 0)
  _append_breakdown(breakdown, "Binnen stuc", binnen_afwerking)

  lagen = 2 if str(payload.get("lagenBinnen")) == "2" else 1
  verf = binnen * 10 * lagen
  _append_breakdown(breakdown, "Binnen schilderwerk", verf)

  kitwerk = binnen * 2.5 if payload.get("kitwerkBinnen") == "ja" else 0
  _append_breakdown(breakdown, "Kitwerk binnen", kitwerk)

  buiten_tarief = 32 if payload.get("afwerkingBuiten") == "alkyd" else 28
  buiten_afwerking = buiten * buiten_tarief
  _append_breakdown(breakdown, "Buiten schilderwerk", buiten_afwerking)

  kozijnen = _to_positive(_to_float(payload.get("kozijnen"))) * 85
  _append_breakdown(breakdown, "Kozijnen/deuren", kozijnen)

  total = sum(item["amount"] for item in breakdown)
  return QuoteResult(total=total, breakdown=breakdown)


def calculate_kozijnen(payload: Dict[str, Any]) -> QuoteResult:
  width_m = _to_positive(_to_float(payload.get("breedte")) / 1000)
  height_m = _to_positive(_to_float(payload.get("hoogte")) / 1000)
  area = width_m * height_m
  basis = {
    "vast": 650,
    "draaikiep": 780,
    "kiepschuif": 1450,
    "hefschuif": 2100,
    "tuindeur": 1650,
  }
  base_price = area * basis.get(payload.get("element"), 600)
  total = base_price
  breakdown: List[Dict[str, float]] = []
  _append_breakdown(breakdown, "Basis", base_price)

  if payload.get("glas") == "triple":
    triple = base_price * 0.18
    total += triple
    _append_breakdown(breakdown, "Triple glas", triple)
  elif payload.get("glas") == "veilig":
    veilig = area * 140
    total += veilig
    _append_breakdown(breakdown, "Veiligheidsglas", veilig)

  if payload.get("roosters") == "per":
    total += 180
    _append_breakdown(breakdown, "Ventilatierooster", 180)

  if payload.get("kleur") == "houtnerf":
    houtnerf = total * 0.12
    total += houtnerf
    _append_breakdown(breakdown, "Houtnerf folie", houtnerf)

  if payload.get("kleurBinnen") == "antraciet":
    total += 220
    _append_breakdown(breakdown, "Binnendeuren RAL", 220)

  if payload.get("veiligheid") == "skg3":
    total += 350
    _append_breakdown(breakdown, "SKG*** + PKVW", 350)

  return QuoteResult(total=total, breakdown=breakdown)


def calculate_loodgieter(payload: Dict[str, Any]) -> QuoteResult:
  basis = {
    "ontstoppen": 225,
    "lek": 295,
    "toilet": 825,
    "wastafel": 495,
    "aansluiting": 375,
  }
  total = float(basis.get(payload.get("pakket"), 0))
  breakdown: List[Dict[str, float]] = []
  _append_breakdown(breakdown, "Pakket", total)

  extra = {"geen": 0, "camera": 185, "sanitair": 350, "badkamer": 750}
  extra_amount = float(extra.get(payload.get("extra"), 0))
  total += extra_amount
  _append_breakdown(breakdown, "Extra", extra_amount)

  aantal = max(1, int(_to_float(payload.get("aantal"), 1)))
  meerwerk = (aantal - 1) * 150
  total += meerwerk
  _append_breakdown(breakdown, "Meerdere ruimtes", meerwerk)

  if payload.get("spoed") == "ja":
    total *= 1.15

  return QuoteResult(total=total, breakdown=breakdown)


def calculate_installaties(payload: Dict[str, Any]) -> QuoteResult:
  basis = {
    "ketel": 3250,
    "hybride": 6850,
    "allelectric": 12800,
    "airco_single": 2650,
    "airco_multi": 4950,
    "zonnepanelen": 5750,
  }
  total = float(basis.get(payload.get("dienst"), 0))
  breakdown: List[Dict[str, float]] = []
  _append_breakdown(breakdown, "Basisset", total)

  capaciteit_factor = {"klein": 0.9, "middel": 1.0, "groot": 1.25}
  factor = capaciteit_factor.get(payload.get("capaciteit"), 1.0)
  if factor != 1.0:
    capacity_extra = total * (factor - 1)
    total += capacity_extra
    _append_breakdown(breakdown, "Capaciteit", capacity_extra)

  pakket_opslag = {"basis": 1.0, "comfort": 1.12, "premium": 1.25}
  pakket_factor = pakket_opslag.get(payload.get("pakket"), 1.0)
  if pakket_factor != 1.0:
    pakket_extra = total * (pakket_factor - 1)
    total += pakket_extra
    _append_breakdown(breakdown, "Pakket-upgrade", pakket_extra)

  extra = {"thermostaat": 275, "onderhoud": 420, "batterij": 3200}
  extra_amount = float(extra.get(payload.get("extra"), 0))
  total += extra_amount
  _append_breakdown(breakdown, "Extra opties", extra_amount)

  if payload.get("net") == "nee":
    total += 450
    _append_breakdown(breakdown, "Betaalde schouw", 450)

  return QuoteResult(total=total, breakdown=breakdown)


SERVICE_CALCULATORS: Dict[str, Callable[[Dict[str, Any]], QuoteResult]] = {
  "uitbouw": calculate_uitbouw,
  "dakkapel": calculate_dakkapel,
  "stuc": calculate_stuc,
  "kozijnen": calculate_kozijnen,
  "loodgieter": calculate_loodgieter,
  "installaties": calculate_installaties,
}


def calculate_quote(service: str, payload: Dict[str, Any] | None) -> Dict[str, Any]:
  if service not in SERVICE_CALCULATORS:
    raise ValueError(f"Onbekende dienst: {service}")
  result = SERVICE_CALCULATORS[service](payload or {})
  return result.to_dict()


__all__ = ["calculate_quote", "SERVICE_CALCULATORS"]
