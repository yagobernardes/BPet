from bop_twin.io.load_config import load_config, ConfigError

def fmt(value, spec=".4f", unit=""):
    if value is None:
        return "N/A"
    try:
        return f"{value:{spec}} {unit}".strip()
    except TypeError:
        return f"{value} {unit}".strip()

try:
    cfg = load_config("configs/ns47.json", convert_to_SI=True)

    print("✅ CONFIG + UNITS CARREGADOS COM SUCESSO!")
    print(f"   Nome do BOP:                {cfg['meta']['name']}")
    print(f"   Bulk modulus (SI):          {cfg['fluid']['bulk_modulus']:.3g} Pa")

    # Exemplo: pega um ram específico
    ram = cfg["rams"]["blind_shear_ram_generic"]

    print(f"   Closing volume (SI):        {fmt(ram.get('closing_volume_m3'), '.5f', 'm³')}")
    print(f"   Main piston diameter (SI):  {fmt(ram.get('main_piston_diameter_m'), '.4f', 'm')}")
    print(f"   Rod diameter (SI):          {fmt(ram.get('rod_diameter_m'), '.4f', 'm')}")
    print(f"   Actuation pressure (SI):    {fmt(ram.get('actuation_pressure_pa'), '.3g', 'Pa')}")

except ConfigError as e:
    print("❌ ERRO DE CONFIGURAÇÃO:", e)
except Exception as e:
    print("❌ ERRO:", e)
    raise