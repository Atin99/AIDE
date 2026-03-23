
ALLOY_DATABASE = {
    "304": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.705,"Cr":0.185,"Ni":0.092,"Mn":0.018},
        "aliases": ["304SS","SS304","AISI 304","UNS S30400","1.4301"],
        "properties": {"yield_MPa":215,"UTS_MPa":505,"elongation_pct":70,"density_gcc":7.93,"Tm_K":1673},
        "applications": ["food processing","chemical plant","kitchen sinks","architectural trim"],
    },
    "304L": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.710,"Cr":0.185,"Ni":0.090,"Mn":0.010,"C":0.002,"Si":0.003},
        "aliases": ["304LSS","UNS S30403","1.4307"],
        "properties": {"yield_MPa":170,"UTS_MPa":485,"elongation_pct":55,"density_gcc":7.93},
        "applications": ["welded structures","chemical tanks"],
    },
    "316L": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.677,"Cr":0.170,"Ni":0.120,"Mo":0.022,"Mn":0.011},
        "aliases": ["316LSS","SS316L","AISI 316L","UNS S31603","1.4404"],
        "properties": {"yield_MPa":170,"UTS_MPa":485,"elongation_pct":50,"density_gcc":7.99,
                        "PREN":24.6,"Tm_K":1648},
        "applications": ["marine hardware","surgical implant","pharmaceutical","coastal bridge"],
    },
    "316H": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.670,"Cr":0.170,"Ni":0.120,"Mo":0.025,"C":0.005,"Mn":0.010},
        "aliases": ["UNS S31609"],
        "properties": {"yield_MPa":205,"UTS_MPa":515,"density_gcc":7.99},
        "applications": ["high temperature service","nuclear primary loops"],
    },
    "321": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.680,"Cr":0.175,"Ni":0.095,"Ti":0.005,"Mn":0.020,"Si":0.005,"C":0.002},
        "aliases": ["321SS","UNS S32100","1.4541"],
        "properties": {"yield_MPa":205,"UTS_MPa":515,"elongation_pct":45,"density_gcc":7.92},
        "applications": ["exhaust manifolds","aircraft engine parts","bellows"],
    },
    "347": {
        "category": "stainless", "subcategory": "austenitic",
        "composition_wt": {"Fe":0.680,"Cr":0.175,"Ni":0.095,"Nb":0.007,"Mn":0.020,"Si":0.005,"C":0.002},
        "aliases": ["347SS","UNS S34700","1.4550"],
        "properties": {"yield_MPa":205,"UTS_MPa":515,"elongation_pct":45,"density_gcc":7.96},
        "applications": ["nuclear pressure vessels","high temperature piping"],
    },
    "2205": {
        "category": "stainless", "subcategory": "duplex",
        "composition_wt": {"Fe":0.680,"Cr":0.220,"Ni":0.055,"Mo":0.031,"N":0.0014,"Mn":0.0126},
        "aliases": ["2205DSS","UNS S31803","1.4462","SAF 2205"],
        "properties": {"yield_MPa":448,"UTS_MPa":621,"elongation_pct":25,"density_gcc":7.82,
                        "PREN":35.3},
        "applications": ["offshore platform","desalination","chemical tanker","pulp and paper"],
    },
    "2507": {
        "category": "stainless", "subcategory": "super duplex",
        "composition_wt": {"Fe":0.640,"Cr":0.250,"Ni":0.070,"Mo":0.040,"N":0.0027},
        "aliases": ["2507SDSS","UNS S32750","1.4410","SAF 2507"],
        "properties": {"yield_MPa":550,"UTS_MPa":800,"elongation_pct":15,"density_gcc":7.81,"PREN":43},
        "applications": ["subsea","deep water","flue gas desulfurisation"],
    },
    "410": {
        "category": "stainless", "subcategory": "martensitic",
        "composition_wt": {"Fe":0.862,"Cr":0.125,"C":0.008,"Mn":0.005},
        "aliases": ["410SS","UNS S41000","1.4006"],
        "properties": {"yield_MPa":275,"UTS_MPa":485,"elongation_pct":20,"density_gcc":7.74},
        "applications": ["valve trim","pump shafts","cutlery"],
    },
    "430": {
        "category": "stainless", "subcategory": "ferritic",
        "composition_wt": {"Fe":0.818,"Cr":0.170,"Mn":0.010,"Si":0.002},
        "aliases": ["430SS","UNS S43000","1.4016"],
        "properties": {"yield_MPa":205,"UTS_MPa":450,"elongation_pct":22,"density_gcc":7.72},
        "applications": ["automotive trim","dishwasher lining","refrigerator panels"],
    },
    "17-4PH": {
        "category": "stainless", "subcategory": "precipitation hardening",
        "composition_wt": {"Fe":0.744,"Cr":0.165,"Ni":0.045,"Cu":0.035,"Nb":0.003,"Mn":0.008},
        "aliases": ["17-4 PH","UNS S17400","1.4542","630"],
        "properties": {"yield_MPa":1100,"UTS_MPa":1170,"elongation_pct":10,"density_gcc":7.78},
        "applications": ["aerospace fasteners","nuclear waste casks","pump shafts"],
    },
    "IN718": {
        "category": "superalloy", "subcategory": "precipitation hardening",
        "composition_wt": {"Ni":0.525,"Cr":0.190,"Fe":0.185,"Nb":0.052,"Mo":0.030,
                           "Al":0.005,"Ti":0.009,"Co":0.004},
        "aliases": ["Inconel 718","Alloy 718","UNS N07718","2.4668"],
        "properties": {"yield_MPa":1035,"UTS_MPa":1240,"elongation_pct":12,"density_gcc":8.19,
                        "Tm_K":1609,"max_service_T_K":923},
        "applications": ["gas turbine disc","rocket motor","cryogenic tank","nuclear fuel spacer"],
    },
    "IN625": {
        "category": "superalloy", "subcategory": "solid solution",
        "composition_wt": {"Ni":0.614,"Cr":0.215,"Mo":0.090,"Fe":0.030,"Nb":0.035,
                           "Al":0.004,"Ti":0.002,"C":0.0005,"Mn":0.002,"Si":0.001},
        "aliases": ["Inconel 625","Alloy 625","UNS N06625","2.4856"],
        "properties": {"yield_MPa":414,"UTS_MPa":827,"elongation_pct":50,"density_gcc":8.44,
                        "Tm_K":1623},
        "applications": ["chemical processing","submarine exhaust","aerospace ducting"],
    },
    "Waspaloy": {
        "category": "superalloy", "subcategory": "precipitation hardening",
        "composition_wt": {"Ni":0.575,"Cr":0.190,"Co":0.135,"Mo":0.043,"Al":0.014,
                           "Ti":0.030,"Fe":0.003,"B":0.0005,"Zr":0.0005},
        "aliases": ["UNS N07001"],
        "properties": {"yield_MPa":795,"UTS_MPa":1275,"density_gcc":8.19,"max_service_T_K":1033},
        "applications": ["turbine blade","compressor disc","jet engine case"],
    },
    "Hastelloy C276": {
        "category": "superalloy", "subcategory": "solid solution",
        "composition_wt": {"Ni":0.570,"Mo":0.160,"Cr":0.155,"Fe":0.055,"W":0.040,
                           "Co":0.025},
        "aliases": ["C276","Alloy C-276","UNS N10276","2.4819"],
        "properties": {"yield_MPa":355,"UTS_MPa":786,"elongation_pct":60,"density_gcc":8.89},
        "applications": ["chemical reactor","pollution control","flue gas scrubber"],
    },
    "CM247LC": {
        "category": "superalloy", "subcategory": "single crystal",
        "composition_wt": {"Ni":0.590,"Cr":0.082,"Co":0.094,"W":0.095,"Al":0.056,
                           "Ta":0.030,"Hf":0.015,"Mo":0.005,"C":0.0007,"B":0.0003},
        "aliases": [],
        "properties": {"density_gcc":8.54,"max_service_T_K":1323},
        "applications": ["single crystal turbine blade","power gen","aerospace HPT"],
    },
    "Ti-6Al-4V": {
        "category": "titanium", "subcategory": "alpha-beta",
        "composition_wt": {"Ti":0.900,"Al":0.060,"V":0.040},
        "aliases": ["Ti64","TC4","Grade 5","UNS R56400","3.7164"],
        "properties": {"yield_MPa":880,"UTS_MPa":950,"elongation_pct":14,"density_gcc":4.43,
                        "Tm_K":1933,"E_GPa":114},
        "applications": ["aerospace structural","hip implant","compressor blade","racing car"],
    },
    "Ti-6Al-2Sn-4Zr-2Mo": {
        "category": "titanium", "subcategory": "near-alpha",
        "composition_wt": {"Ti":0.880,"Al":0.060,"Zr":0.020,"Sn":0.020,"Mo":0.020},
        "aliases": ["Ti-6242","Ti-6242S"],
        "properties": {"yield_MPa":917,"UTS_MPa":1000,"density_gcc":4.54,"max_service_T_K":813},
        "applications": ["compressor disc","high temperature aero"],
    },
    "CP-Ti Grade 2": {
        "category": "titanium", "subcategory": "commercially pure",
        "composition_wt": {"Ti":0.995,"Fe":0.003,"O":0.002},
        "aliases": ["Grade 2","CP Ti","UNS R50400"],
        "properties": {"yield_MPa":275,"UTS_MPa":345,"elongation_pct":20,"density_gcc":4.51},
        "applications": ["chemical plant","marine heat exchanger","prosthetic"],
    },
    "Ti-15V-3Cr-3Sn-3Al": {
        "category": "titanium", "subcategory": "beta",
        "composition_wt": {"Ti":0.760,"V":0.150,"Cr":0.030,"Sn":0.030,"Al":0.030},
        "aliases": ["Ti-15-3","Beta alloy"],
        "properties": {"yield_MPa":1100,"UTS_MPa":1170,"density_gcc":4.76},
        "applications": ["aerospace spring","hydraulic tubing"],
    },
    "2024-T3": {
        "category": "aluminium", "subcategory": "2xxx Cu",
        "composition_wt": {"Al":0.932,"Cu":0.044,"Mg":0.015,"Mn":0.006,"Fe":0.002,"Si":0.001},
        "aliases": ["AA2024","2024","UNS A92024"],
        "properties": {"yield_MPa":345,"UTS_MPa":483,"elongation_pct":18,"density_gcc":2.78,"E_GPa":73},
        "applications": ["aircraft fuselage","wing skin","truck wheel"],
    },
    "6061-T6": {
        "category": "aluminium", "subcategory": "6xxx Mg-Si",
        "composition_wt": {"Al":0.969,"Mg":0.010,"Si":0.006,"Cu":0.003,"Mn":0.0015,"Cr":0.002},
        "aliases": ["AA6061","6061","UNS A96061"],
        "properties": {"yield_MPa":276,"UTS_MPa":310,"elongation_pct":12,"density_gcc":2.70,"E_GPa":69},
        "applications": ["bicycle frame","structural beam","marine fitting"],
    },
    "7075-T6": {
        "category": "aluminium", "subcategory": "7xxx Zn",
        "composition_wt": {"Al":0.899,"Zn":0.056,"Mg":0.025,"Cu":0.016,"Cr":0.002,"Mn":0.001,"Si":0.001},
        "aliases": ["AA7075","7075","UNS A97075"],
        "properties": {"yield_MPa":503,"UTS_MPa":572,"elongation_pct":11,"density_gcc":2.81,"E_GPa":72},
        "applications": ["aircraft wing spar","rock climbing gear","M16 rifle receiver"],
    },
    "5083-H116": {
        "category": "aluminium", "subcategory": "5xxx Mg",
        "composition_wt": {"Al":0.944,"Mg":0.043,"Mn":0.007,"Cr":0.001,"Fe":0.004,"Si":0.001},
        "aliases": ["AA5083","5083"],
        "properties": {"yield_MPa":228,"UTS_MPa":317,"elongation_pct":16,"density_gcc":2.66},
        "applications": ["ship hull","pressure vessel","cryogenic","LNG tank"],
    },
    "CoCrFeMnNi": {
        "category": "HEA", "subcategory": "Cantor alloy",
        "composition_wt": {"Co":0.200,"Cr":0.200,"Fe":0.200,"Mn":0.200,"Ni":0.200},
        "aliases": ["Cantor","Cantor alloy","equiatomic CoCrFeMnNi"],
        "properties": {"yield_MPa":125,"UTS_MPa":450,"elongation_pct":65,"density_gcc":8.05,
                        "delta_pct":1.12,"VEC":8.0},
        "applications": ["cryogenic structural","research benchmark"],
    },
    "AlCoCrFeNi": {
        "category": "HEA", "subcategory": "BCC/B2 HEA",
        "composition_wt": {"Al":0.200,"Co":0.200,"Cr":0.200,"Fe":0.200,"Ni":0.200},
        "aliases": ["Al equiatomic HEA"],
        "properties": {"yield_MPa":1350,"UTS_MPa":1480,"density_gcc":6.67,"VEC":7.2},
        "applications": ["high strength structural","wear resistant"],
    },
    "TiZrNbMoV": {
        "category": "HEA", "subcategory": "refractory HEA",
        "composition_wt": {"Ti":0.200,"Zr":0.200,"Nb":0.200,"Mo":0.200,"V":0.200},
        "aliases": ["refractory HEA"],
        "properties": {"density_gcc":7.15},
        "applications": ["high temperature structural"],
    },
    "Stellite 6": {
        "category": "cobalt", "subcategory": "wear resistant",
        "composition_wt": {"Co":0.600,"Cr":0.280,"W":0.040,"C":0.012,"Ni":0.025,
                           "Fe":0.015,"Si":0.008,"Mn":0.010},
        "aliases": ["Stellite6","Haynes 6"],
        "properties": {"density_gcc":8.39},
        "applications": ["valve seat","pump sleeve","hot wire guide"],
    },
    "Haynes 25": {
        "category": "cobalt", "subcategory": "solid solution",
        "composition_wt": {"Co":0.500,"Cr":0.200,"W":0.150,"Ni":0.100,"Fe":0.030,
                           "C":0.010,"Mn":0.010},
        "aliases": ["L-605","UNS R30605"],
        "properties": {"yield_MPa":445,"UTS_MPa":1000,"density_gcc":9.13},
        "applications": ["gas turbine combustor","heart valve spring"],
    },
    "C26000": {
        "category": "copper", "subcategory": "brass",
        "composition_wt": {"Cu":0.700,"Zn":0.300},
        "aliases": ["Cartridge Brass","70-30 brass","CuZn30"],
        "properties": {"yield_MPa":110,"UTS_MPa":340,"elongation_pct":63,"density_gcc":8.53},
        "applications": ["ammunition cartridge","lamp fitting","radiator core"],
    },
    "C95400": {
        "category": "copper", "subcategory": "aluminium bronze",
        "composition_wt": {"Cu":0.860,"Al":0.110,"Fe":0.030},
        "aliases": ["Al Bronze","aluminium bronze"],
        "properties": {"yield_MPa":240,"UTS_MPa":585,"elongation_pct":12,"density_gcc":7.45},
        "applications": ["marine propeller","pump impeller","valve body"],
    },
    "Zircaloy-4": {
        "category": "nuclear", "subcategory": "cladding",
        "composition_wt": {"Zr":0.981,"Sn":0.015,"Fe":0.002,"Cr":0.001,"O":0.001},
        "aliases": ["Zry-4","Zircaloy 4"],
        "properties": {"yield_MPa":380,"UTS_MPa":510,"density_gcc":6.56,"Tm_K":2125,"neutron_xs_b":0.18},
        "applications": ["PWR fuel cladding","BWR fuel channel"],
    },
    "Zircaloy-2": {
        "category": "nuclear", "subcategory": "cladding",
        "composition_wt": {"Zr":0.981,"Sn":0.015,"Fe":0.001,"Cr":0.001,"Ni":0.001,"O":0.001},
        "aliases": ["Zry-2","Zircaloy 2"],
        "properties": {"density_gcc":6.55,"neutron_xs_b":0.18},
        "applications": ["BWR fuel cladding"],
    },
    "NbMoTaW": {
        "category": "refractory", "subcategory": "refractory HEA",
        "composition_wt": {"Nb":0.250,"Mo":0.250,"Ta":0.250,"W":0.250},
        "aliases": ["RMPEA","refractory MPEA"],
        "properties": {"density_gcc":13.75,"Tm_K":3073},
        "applications": ["ultra high temperature","HIP tooling"],
    },
    "H13": {
        "category": "tool_steel", "subcategory": "hot work",
        "composition_wt": {"Fe":0.913,"Cr":0.052,"Mo":0.013,"V":0.010,"Si":0.010,"C":0.004},
        "aliases": ["AISI H13","1.2344","SKD61"],
        "properties": {"yield_MPa":1380,"UTS_MPa":1590,"density_gcc":7.80},
        "applications": ["die casting die","extrusion die","forging tooling"],
    },
    "M2": {
        "category": "tool_steel", "subcategory": "high speed",
        "composition_wt": {"Fe":0.820,"W":0.063,"Mo":0.050,"Cr":0.042,"V":0.019,"C":0.009},
        "aliases": ["HSS M2","1.3343","SKH51"],
        "properties": {"yield_MPa":None,"UTS_MPa":None,"density_gcc":8.16},
        "applications": ["drill bit","tap","milling cutter","saw blade"],
    },
    "D2": {
        "category": "tool_steel", "subcategory": "cold work",
        "composition_wt": {"Fe":0.852,"Cr":0.120,"C":0.015,"Mo":0.010,"V":0.010},
        "aliases": ["AISI D2","1.2379","SKD11"],
        "properties": {"density_gcc":7.70},
        "applications": ["blanking die","stamping die","thread rolling die"],
    },
    "AZ31B": {
        "category": "magnesium", "subcategory": "wrought",
        "composition_wt": {"Mg":0.960,"Al":0.030,"Zn":0.010},
        "aliases": ["AZ31","UNS M11311"],
        "properties": {"yield_MPa":150,"UTS_MPa":255,"elongation_pct":15,"density_gcc":1.77},
        "applications": ["automotive panel","laptop casing","UAV structure"],
    },
    "WE43": {
        "category": "magnesium", "subcategory": "rare earth",
        "composition_wt": {"Mg":0.948,"Y":0.040,"Zr":0.004,"Nd":0.008},
        "aliases": ["UNS M18430"],
        "properties": {"yield_MPa":195,"UTS_MPa":285,"density_gcc":1.84},
        "applications": ["helicopter gearbox","bioabsorbable implant"],
    },
}


def lookup_alloy(name: str) -> dict | None:
    name_clean = name.strip().upper().replace(" ", "").replace("-", "")
    for key, data in ALLOY_DATABASE.items():
        key_clean = key.upper().replace(" ", "").replace("-", "")
        if name_clean == key_clean:
            return {"key": key, **data}
        for alias in data.get("aliases", []):
            alias_clean = alias.upper().replace(" ", "").replace("-", "")
            if name_clean == alias_clean:
                return {"key": key, **data}
    for key, data in ALLOY_DATABASE.items():
        key_clean = key.upper().replace(" ", "").replace("-", "")
        if name_clean in key_clean or key_clean in name_clean:
            return {"key": key, **data}
        for alias in data.get("aliases", []):
            alias_clean = alias.upper().replace(" ", "").replace("-", "")
            if name_clean in alias_clean or alias_clean in name_clean:
                return {"key": key, **data}
    return None


def get_alloys_by_category(category: str) -> list:
    return [{"key": k, **v} for k, v in ALLOY_DATABASE.items()
            if v.get("category", "").lower() == category.lower()]


def search_alloys(query: str) -> list:
    q = query.lower()
    results = []
    for key, data in ALLOY_DATABASE.items():
        searchable = f"{key} {data.get('category','')} {data.get('subcategory','')} {' '.join(data.get('applications',[]))} {' '.join(data.get('aliases',[]))}"
        if q in searchable.lower():
            results.append({"key": key, **data})
    return results
