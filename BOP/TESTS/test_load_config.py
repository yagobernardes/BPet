from bop_twin.io.load_config import load_config, ConfigError

def main():
    try:
        cfg = load_config("configs/ns47.json", convert_to_SI=True)
        print("✅ CONFIG + UNITS CARREGADOS COM SUCESSO!")
        print("   Nome do BOP:", cfg["meta"]["name"])
        print("   Bulk modulus (SI):", cfg["fluid"]["bulk_modulus"], "Pa")
    except ConfigError as e:
        print("❌ ERRO DE CONFIGURAÇÃO:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()