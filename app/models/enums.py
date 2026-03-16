"""Canonical enumerations for oncology data abstraction."""

from enum import Enum


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class CancerType(str, Enum):
    LUNG = "lung"
    BREAST = "breast"
    COLORECTAL = "colorectal"
    PROSTATE = "prostate"
    HEAD_NECK = "head_neck"
    LIVER = "liver"
    ESOPHAGEAL = "esophageal"
    GASTRIC = "gastric"
    PANCREATIC = "pancreatic"
    CERVICAL = "cervical"
    OTHER = "other"


class HistologyGroup(str, Enum):
    NSCLC_ADENO = "nsclc_adenocarcinoma"
    NSCLC_SQUAMOUS = "nsclc_squamous"
    NSCLC_LARGE_CELL = "nsclc_large_cell"
    NSCLC_NOS = "nsclc_nos"
    SCLC = "sclc"
    IDC = "idc"  # invasive ductal carcinoma
    ILC = "ilc"  # invasive lobular carcinoma
    DCIS = "dcis"
    OTHER = "other"
    UNKNOWN = "unknown"


class Grade(str, Enum):
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"
    GX = "GX"


class ClinicalStageGroup(str, Enum):
    STAGE_0 = "0"
    STAGE_I = "I"
    STAGE_IA = "IA"
    STAGE_IB = "IB"
    STAGE_II = "II"
    STAGE_IIA = "IIA"
    STAGE_IIB = "IIB"
    STAGE_III = "III"
    STAGE_IIIA = "IIIA"
    STAGE_IIIB = "IIIB"
    STAGE_IIIC = "IIIC"
    STAGE_IV = "IV"
    STAGE_IVA = "IVA"
    STAGE_IVB = "IVB"
    UNKNOWN = "unknown"


class StagingSystem(str, Enum):
    AJCC_8TH = "AJCC_8th"
    AJCC_7TH = "AJCC_7th"
    VALSG = "VALSG"  # Veterans Admin Lung Study Group (SCLC)
    FIGO = "FIGO"
    OTHER = "other"


class RECISTCategory(str, Enum):
    CR = "CR"  # Complete response
    PR = "PR"  # Partial response
    SD = "SD"  # Stable disease
    PD = "PD"  # Progressive disease
    NE = "NE"  # Not evaluable


class TreatmentIntent(str, Enum):
    CURATIVE = "curative"
    PALLIATIVE = "palliative"
    ADJUVANT = "adjuvant"
    NEOADJUVANT = "neoadjuvant"
    DEFINITIVE = "definitive"
    SALVAGE = "salvage"
    UNKNOWN = "unknown"


class TreatmentModality(str, Enum):
    CHEMOTHERAPY = "chemotherapy"
    IMMUNOTHERAPY = "immunotherapy"
    TARGETED_THERAPY = "targeted_therapy"
    ENDOCRINE_THERAPY = "endocrine_therapy"
    RADIATION_EBRT = "radiation_ebrt"
    RADIATION_SBRT = "radiation_sbrt"
    RADIATION_PROTON = "radiation_proton"
    RADIATION_BRACHY = "radiation_brachytherapy"
    SURGERY = "surgery"
    OTHER = "other"


class ProgressionType(str, Enum):
    LOCAL = "local"
    REGIONAL = "regional"
    DISTANT = "distant"
    UNKNOWN = "unknown"


class VitalStatus(str, Enum):
    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractionMethod(str, Enum):
    STRUCTURED = "structured"
    RULE = "rule"
    NLP = "nlp"
    MANUAL = "manual"
    DERIVED = "derived"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class DocumentType(str, Enum):
    CONSULTATION_NOTE = "consultation_note"
    PROGRESS_NOTE = "progress_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    RADIOLOGY_REPORT = "radiology_report"
    PATHOLOGY_REPORT = "pathology_report"
    OPERATIVE_NOTE = "operative_note"
    LAB_REPORT = "lab_report"
    TREATMENT_SUMMARY = "treatment_summary"
    EXTERNAL_RECORD = "external_record"
    IMAGE = "image"
    OTHER = "other"


class EncounterType(str, Enum):
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    EMERGENCY = "emergency"
    TELEHEALTH = "telehealth"
    OTHER = "other"
