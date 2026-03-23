
DOMAIN_DEPS = {
    "Thermodynamics": [],
    "Hume-Rothery": ["Thermodynamics", "Phase Stability"],
    "Mechanical": ["Hume-Rothery"],
    "Corrosion": ["Thermodynamics", "Phase Stability", "Electronic Structure"],
    "Oxidation": ["Thermodynamics", "Surface Energy"],
    "Radiation Physics": ["Diffusion", "Phase Stability"],
    "Weldability": ["Transformation Kinetics", "Phase Stability", "Mechanical"],
    "Creep": ["Thermodynamics", "Diffusion", "Mechanical"],
    "Fatigue & Fracture": ["Mechanical", "Phase Stability", "Grain Boundary"],
    "Grain Boundary": ["Thermodynamics", "Diffusion"],
    "Hydrogen Embrittlement": ["Diffusion", "Mechanical", "Grain Boundary"],
    "Magnetism": ["Electronic Structure"],
    "Thermal Properties": ["Thermodynamics"],
    "Regulatory & Safety": [],
    "Electronic Structure": ["Hume-Rothery"],
    "Superconductivity": ["Electronic Structure", "Thermodynamics"],
    "Phase Stability": ["Thermodynamics", "Hume-Rothery"],
    "Plasticity": ["Mechanical", "Grain Boundary"],
    "Diffusion": ["Thermodynamics"],
    "Surface Energy": ["Electronic Structure"],
    "Tribology & Wear": ["Mechanical", "Surface Energy"],
    "Acoustic Properties": ["Mechanical"],
    "Shape Memory": ["Phase Stability", "Mechanical"],
    "Catalysis": ["Electronic Structure", "Surface Energy"],
    "Biocompatibility": ["Corrosion", "Regulatory & Safety"],
    "Relativistic Effects": ["Electronic Structure"],
    "Nuclear Fuel Compatibility": ["Radiation Physics", "Corrosion"],
    "Optical Properties": ["Electronic Structure"],
    "Hydrogen Storage": ["Thermodynamics", "Diffusion"],
    "Structural Efficiency": ["Mechanical"],
    "CALPHAD Stability": ["Thermodynamics", "Phase Stability"],
    "India Corrosion Index": ["Corrosion"],
    "Transformation Kinetics": ["Thermodynamics", "Diffusion"],
    "Castability": ["Thermodynamics"],
    "Machinability": ["Mechanical"],
    "Formability": ["Mechanical", "Plasticity"],
    "Additive Manufacturing": ["Thermodynamics", "Weldability"],
    "Heat Treatment Response": ["Phase Stability", "Transformation Kinetics"],
    "Fracture Mechanics": ["Mechanical", "Fatigue & Fracture"],
    "Impact Toughness": ["Mechanical", "Grain Boundary"],
    "Galvanic Compatibility": ["Corrosion", "Electronic Structure"],
    "Solidification": ["Thermodynamics", "Castability"],
}

DOMAIN_GROUPS = {
    "structural": [
        "Mechanical", "Fatigue & Fracture", "Creep", "Impact Toughness",
        "Fracture Mechanics", "Structural Efficiency",
    ],
    "corrosion": [
        "Corrosion", "Oxidation", "Galvanic Compatibility",
        "India Corrosion Index", "Hydrogen Embrittlement",
    ],
    "manufacturing": [
        "Weldability", "Castability", "Machinability", "Formability",
        "Additive Manufacturing", "Heat Treatment Response",
    ],
    "thermal": [
        "Thermodynamics", "Thermal Properties", "Creep", "Diffusion",
    ],
    "biomedical": [
        "Biocompatibility", "Corrosion", "Mechanical", "Regulatory & Safety",
    ],
    "nuclear": [
        "Radiation Physics", "Nuclear Fuel Compatibility", "Corrosion",
        "Creep", "Hydrogen Embrittlement",
    ],
    "electronic": [
        "Electronic Structure", "Magnetism", "Superconductivity",
        "Optical Properties",
    ],
}


def get_related_domains(domain_name: str) -> list[str]:
    return DOMAIN_DEPS.get(domain_name, [])


def get_cascade_domains(failed_domains: list[str]) -> set[str]:
    to_check = set()
    for d in failed_domains:
        to_check.update(DOMAIN_DEPS.get(d, []))
    to_check -= set(failed_domains)
    return to_check


def get_domain_group(group_name: str) -> list[str]:
    return DOMAIN_GROUPS.get(group_name.lower(), [])
