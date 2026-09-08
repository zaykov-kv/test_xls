from typing import Dict, List
from icd_parser import parse_icd_codes, has_condition

# --- СПРАВОЧНИК КОДОВ ДЛЯ ELIXHAUSER (все 31 категория) ---
ELIXHAUSER_MAPPINGS: Dict[str, List[str]] = {
    'Congestive heart failure': ['I09.9', 'I11.0', 'I13.0', 'I13.2', 'I25.5', 'I42.0', 'I42.5', 'I42.6', 'I42.7', 'I42.8', 'I42.9', 'I43', 'I50', 'P29.0'],
    'Cardiac arrhythmias': ['I44.1', 'I44.2', 'I44.3', 'I45.6', 'I45.9', 'I47', 'I48', 'I49', 'R00.0', 'R00.1', 'R00.8', 'T82.1', 'Z45.0', 'Z95.0'],
    'Valvular disease': ['A52.0', 'I05', 'I06', 'I07', 'I08', 'I09.1', 'I09.8', 'I34', 'I35', 'I36', 'I37', 'I38', 'I39', 'Q23.0', 'Q23.1', 'Q23.2', 'Q23.3', 'Z95.2', 'Z95.3', 'Z95.4'],
    'Pulmonary circulation disorders': ['I26', 'I27', 'I28.0', 'I28.8', 'I28.9'],
    'Peripheral vascular disorders': ['I70', 'I71', 'I73.1', 'I73.8', 'I73.9', 'I77.1', 'I79.0', 'I79.2', 'K55.1', 'K55.8', 'K55.9', 'Z95.8', 'Z95.9'],
    'Hypertension, uncomplicated': ['I10'],
    'Hypertension, complicated': ['I11', 'I12', 'I13', 'I15'],
    'Paralysis': ['G04.1', 'G11.4', 'G80.1', 'G80.2', 'G81', 'G82', 'G83.0', 'G83.1', 'G83.2', 'G83.3', 'G83.4', 'G83.9'],
    'Other neurological disorders': ['G35', 'G36', 'G37', 'G40', 'G41', 'G93.4', 'G93.5', 'R47.0', 'R56.0', 'R56.1', 'R56.8', 'R56.9'],
    'Chronic pulmonary disease': ['I27.8', 'I27.9', 'J40', 'J41', 'J42', 'J43', 'J44', 'J45', 'J46', 'J47', 'J60', 'J61', 'J62', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68.4', 'J70.1', 'J70.3'],
    'Diabetes, uncomplicated': ['E10.0', 'E10.1', 'E10.9', 'E11.0', 'E11.1', 'E11.9', 'E12.0', 'E12.1', 'E12.9', 'E13.0', 'E13.1', 'E13.9', 'E14.0', 'E14.1', 'E14.9'],
    'Diabetes, complicated': ['E10.2', 'E10.3', 'E10.4', 'E10.5', 'E10.6', 'E10.7', 'E10.8', 'E11.2', 'E11.3', 'E11.4', 'E11.5', 'E11.6', 'E11.7', 'E11.8', 'E12.2', 'E12.3', 'E12.4', 'E12.5', 'E12.6', 'E12.7', 'E12.8', 'E13.2', 'E13.3', 'E13.4', 'E13.5', 'E13.6', 'E13.7', 'E13.8', 'E14.2', 'E14.3', 'E14.4', 'E14.5', 'E14.6', 'E14.7', 'E14.8'],
    'Hypothyroidism': ['E00', 'E01', 'E02', 'E03', 'E89.0'],
    'Renal failure': ['I12.0', 'I13.1', 'N18', 'N19', 'N25.0', 'Z49.0', 'Z49.1', 'Z49.2', 'Z94.0', 'Z99.2'],
    'Liver disease': ['B18', 'I85', 'I86.4', 'I98.2', 'K70', 'K71.1', 'K71.3', 'K71.4', 'K71.5', 'K71.7', 'K72', 'K73', 'K74', 'K76.0', 'K76.2', 'K76.3', 'K76.4', 'K76.5', 'K76.6', 'K76.7', 'K76.8', 'K76.9', 'Z94.4'],
    'Peptic ulcer disease excluding bleeding': ['K25.7', 'K25.9', 'K26.7', 'K26.9', 'K27.7', 'K27.9', 'K28.7', 'K28.9'],
    'AIDS/HIV': ['B20', 'B21', 'B22', 'B24'],
    'Lymphoma': ['C81', 'C82', 'C83', 'C84', 'C85', 'C88', 'C96', 'C90.0', 'C90.2'],
    'Metastatic cancer': ['C77', 'C78', 'C79', 'C80'],
    'Solid tumor without metastasis': ['C00', 'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19', 'C20', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'C30', 'C31', 'C32', 'C33', 'C34', 'C37', 'C38', 'C39', 'C40', 'C41', 'C43', 'C45', 'C46', 'C47', 'C48', 'C49', 'C50', 'C51', 'C52', 'C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C60', 'C61', 'C62', 'C63', 'C64', 'C65', 'C66', 'C67', 'C68', 'C69', 'C70', 'C71', 'C72', 'C73', 'C74', 'C75', 'C76', 'C97'],
    'Rheumatoid arthritis/collagen vascular diseases': ['L94.0', 'L94.1', 'L94.3', 'M05', 'M06', 'M08', 'M12.0', 'M12.3', 'M30', 'M31.0', 'M31.1', 'M31.2', 'M31.3', 'M32', 'M33', 'M34', 'M35', 'M45', 'M46.1', 'M46.8', 'M46.9'],
    'Coagulopathy': ['D65', 'D66', 'D67', 'D68', 'D69.1', 'D69.3', 'D69.4', 'D69.5', 'D69.6'],
    'Obesity': ['E66'],
    'Weight loss': ['E40', 'E41', 'E42', 'E43', 'E44', 'E45', 'E46', 'R63.4', 'R64'],
    'Fluid and electrolyte disorders': ['E22.2', 'E86', 'E87'],
    'Blood loss anemia': ['D50.0'],
    'Deficiency anemia': ['D50.8', 'D50.9', 'D51', 'D52', 'D53'],
    'Alcohol abuse': ['F10', 'E52', 'G62.1', 'I42.6', 'K29.2', 'K70.0', 'K70.3', 'K70.9', 'T51', 'Z50.2', 'Z71.4', 'Z72.1'],
    'Drug abuse': ['F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F18', 'F19', 'Z71.5', 'Z72.2'],
    'Psychoses': ['F20', 'F22', 'F23', 'F24', 'F25', 'F28', 'F29', 'F30.2', 'F31.2', 'F31.5'],
    'Depression': ['F20.4', 'F31.3', 'F31.4', 'F31.5', 'F32', 'F33', 'F34.1', 'F41.2', 'F43.2']
}


def evaluate_elixhauser(icd_codes_text: str) -> Dict[str, int]:
    """
    Оценивает пациента по всем 31 категории Elixhauser.
    """
    patient_codes = parse_icd_codes(icd_codes_text)
    if not patient_codes:
        return {cat: 0 for cat in ELIXHAUSER_MAPPINGS.keys()}
    
    results = {}
    for category, codes in ELIXHAUSER_MAPPINGS.items():
        results[category] = has_condition(patient_codes, codes)
    
    return results


def calculate_elixhauser_scores(results: Dict[str, int]) -> Dict[str, int]:
    """
    Рассчитывает AHRQ и van Walraven баллы Elixhauser с полной условной логикой.
    Полностью соответствует формулам из Excel.
    """
    
    # Извлекаем значения для удобства
    CHF = results.get('Congestive heart failure', 0)
    ARR = results.get('Cardiac arrhythmias', 0)
    VALV = results.get('Valvular disease', 0)
    PULM = results.get('Pulmonary circulation disorders', 0)
    PERI = results.get('Peripheral vascular disorders', 0)
    HTN_U = results.get('Hypertension, uncomplicated', 0)
    HTN_C = results.get('Hypertension, complicated', 0)
    PARA = results.get('Paralysis', 0)
    NEURO = results.get('Other neurological disorders', 0)
    COPD = results.get('Chronic pulmonary disease', 0)
    DIAB_U = results.get('Diabetes, uncomplicated', 0)
    DIAB_C = results.get('Diabetes, complicated', 0)
    HYPO = results.get('Hypothyroidism', 0)
    RENAL = results.get('Renal failure', 0)
    LIVER = results.get('Liver disease', 0)
    ULCER = results.get('Peptic ulcer disease excluding bleeding', 0)
    AIDS = results.get('AIDS/HIV', 0)
    LYMPH = results.get('Lymphoma', 0)
    METS = results.get('Metastatic cancer', 0)
    TUMOR = results.get('Solid tumor without metastasis', 0)
    RHEUM = results.get('Rheumatoid arthritis/collagen vascular diseases', 0)
    COAG = results.get('Coagulopathy', 0)
    OBES = results.get('Obesity', 0)
    WEIGHT = results.get('Weight loss', 0)
    FLUID = results.get('Fluid and electrolyte disorders', 0)
    BLOOD = results.get('Blood loss anemia', 0)
    ANEMIA = results.get('Deficiency anemia', 0)
    ALC = results.get('Alcohol abuse', 0)
    DRUG = results.get('Drug abuse', 0)
    PSYCH = results.get('Psychoses', 0)
    DEPR = results.get('Depression', 0)
    
    # --- AHRQ Elixhauser score (полное соответствие Excel) ---
    # Формула из Excel:
    # =(C2*9)+(D2*0)+(E2*0)+(F2*6)+(G2*3)+
    #  IF(I2=0,H2*-1,0)+(I2*-1)+
    #  (J2*5)+(K2*5)+(L2*3)+
    #  IF(N2=0,M2*0,0)+(N2*-3)+
    #  (O2*0)+(P2*6)+(Q2*4)+(R2*0)+(S2*0)+(T2*6)+
    #  (U2*14)+IF(U2=0,V2*7,0)+(W2*0)+
    #  (X2*11)+(Y2*-5)+(Z2*9)+(AA2*11)+(AB2*-3)+(AC2*-2)+(AD2*-1)+(AE2*-7)+(AF2*-5)+(AG2*-5)
    
    ahrq = (
        CHF * 9 +
        ARR * 0 +
        VALV * 0 +
        PULM * 6 +
        PERI * 3 +
        (HTN_U * -1 if HTN_C == 0 else 0) +
        HTN_C * -1 +
        PARA * 5 +
        NEURO * 5 +
        COPD * 3 +
        (DIAB_U * 0 if DIAB_C == 0 else 0) +
        DIAB_C * -3 +
        HYPO * 0 +
        RENAL * 6 +
        LIVER * 4 +
        ULCER * 0 +
        AIDS * 0 +
        LYMPH * 6 +
        METS * 14 +
        TUMOR * 7 +
        RHEUM * 0 +
        COAG * 11 +
        OBES * -5 +
        WEIGHT * 9 +
        FLUID * 11 +
        BLOOD * -3 +
        ANEMIA * -2 +
        ALC * -1 +
        DRUG * -7 +
        PSYCH * -5 +
        DEPR * -5
    )
    
    # --- van Walraven Elixhauser score (полное соответствие Excel) ---
    # Формула из Excel:
    # =(C2*7)+(D2*5)+(E2*-1)+(F2*4)+(G2*2)+
    #  IF(I2=0,H2*0)+(I2*0)+
    #  (J2*7)+(K2*6)+(L2*3)+
    #  IF(N2=0,M2*0,0)+(N2*0)+
    #  (O2*0)+(P2*5)+(Q2*11)+(R2*0)+(S2*0)+
    #  (T2*9)+(U2*12)+IF(U2=0,V2*4,0)+(W2*0)+
    #  (X2*3)+(Y2*-4)+(Z2*6)+(AA2*5)+(AB2*-2)+(AC2*-2)+(AD2*0)+(AE2*-7)+(AF2*0)+(AG2*-3)
    
    van_walraven = (
        CHF * 7 +
        ARR * 5 +
        VALV * -1 +
        PULM * 4 +
        PERI * 2 +
        (HTN_U * 0 if HTN_C == 0 else 0) +
        HTN_C * 0 +
        PARA * 7 +
        NEURO * 6 +
        COPD * 3 +
        (DIAB_U * 0 if DIAB_C == 0 else 0) +
        DIAB_C * 0 +
        HYPO * 0 +
        RENAL * 5 +
        LIVER * 11 +
        ULCER * 0 +
        AIDS * 0 +
        LYMPH * 9 +
        METS * 12 +
        TUMOR * 4 +
        RHEUM * 0 +
        COAG * 3 +
        OBES * -4 +
        WEIGHT * 6 +
        FLUID * 5 +
        BLOOD * -2 +
        ANEMIA * -2 +
        ALC * 0 +
        DRUG * -7 +
        PSYCH * 0 +
        DEPR * -3
    )
    
    return {
        'AHRQ Elixhauser': ahrq,
        'van Walraven Elixhauser': van_walraven
    }