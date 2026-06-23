# -*- coding: utf-8 -*-

import json
import random

from .bozppo_config import TRAINING_CONTENT_FILE

TRAINING_SECTIONS = [
    (
        "1. Vítejte ve společnosti",
        "Vstupní školení je určeno pro nové zaměstnance před zahájením práce. Cílem je seznámit se "
        "se základními pravidly firmy, bezpečným pohybem na pracovišti, ochranou informací, "
        "pracovními návyky a postupy při mimořádných událostech. Pokud něčemu nerozumíte, ptejte se "
        "nadřízeného, školitele nebo pověřené osoby ještě před zahájením činnosti.",
    ),
    (
        "2. Pracovní režim a odpovědnost",
        "Zaměstnanec dodržuje pracovní dobu, evidenci docházky, interní předpisy a pokyny nadřízeného. "
        "Pracuje pouze na úkolech, ke kterým byl zaškolen a které odpovídají jeho kvalifikaci. "
        "Změny směn, nepřítomnost, návštěvu lékaře nebo překážku v práci oznamuje podle firemních pravidel.",
    ),
    (
        "3. Bezpečnost a ochrana zdraví při práci",
        "Na pracovišti je nutné udržovat pořádek, používat předepsané osobní ochranné pracovní prostředky "
        "a respektovat bezpečnostní značení. Zaměstnanec nesmí obcházet ochranná zařízení, vstupovat do "
        "nepovolených prostor ani obsluhovat zařízení, pro které nemá zaškolení nebo oprávnění.",
    ),
    (
        "4. Požární ochrana a evakuace",
        "Dodržujte zákaz kouření a manipulace s otevřeným ohněm mimo povolená místa. Únikové cesty, "
        "hasicí přístroje a hydranty musí zůstat volné. Při požáru varujte osoby v okolí, volejte pomoc, "
        "postupujte podle evakuačních pokynů a hasicí prostředek použijte jen tehdy, pokud je to bezpečné.",
    ),
    (
        "5. První pomoc a hlášení událostí",
        "Každý pracovní úraz, nebezpečnou situaci, poškození zařízení, únik látky nebo téměř nehodu "
        "ihned oznamte nadřízenému. První pomoc poskytujte podle svých schopností a při ohrožení života "
        "volejte 155 nebo 112. Události se neodkládají na konec směny.",
    ),
    (
        "6. Ochrana majetku a informací",
        "Firemní zařízení, dokumenty, přístupové karty, hesla a interní informace používejte pouze k práci. "
        "Hesla nesdílejte, pracovní zařízení nenechávejte bez dozoru a podezřelé e-maily nebo ztrátu "
        "zařízení neprodleně oznamte. Informace o zákaznících, zaměstnancích a provozu se nesdělují "
        "neoprávněným osobám.",
    ),
    (
        "7. Firemní kultura a komunikace",
        "Chováme se slušně, spolupracujeme a respektujeme kolegy, zákazníky i návštěvy. Šikana, diskriminace, "
        "obtěžování, alkohol nebo jiné návykové látky na pracovišti nejsou přípustné. Problémy řešte včas "
        "s nadřízeným, personalistou nebo jinou pověřenou osobou.",
    ),
]


LEGAL_SECTIONS = [
    (
        "8. Základní právní rámec",
        "Přehled je informativní a je určen pro základní orientaci nových zaměstnanců. "
        "Vždy se řiďte aktuálním zněním právních předpisů, místní dokumentací objednatele, pokyny odpovědné osoby "
        "a konkrétním předáním pracoviště. Ověřeno k 17.05.2026.",
    ),
    (
        "8.1 Základní předpisy BOZP",
        "Zákon č. 262/2006 Sb., zákoník práce, zejména část věnovaná bezpečnosti a ochraně zdraví při práci, "
        "upravuje prevenci rizik, školení zaměstnanců, poskytování OOPP, povinnosti zaměstnavatele i povinnosti "
        "zaměstnanců. Zákon č. 309/2006 Sb. doplňuje požadavky na pracoviště, pracovní prostředí, bezpečnostní značky, "
        "prevenci rizik a některé povinnosti při stavebních a dalších rizikových činnostech.",
    ),
    (
        "8.2 Pracoviště, zařízení, OOPP a značení",
        "Nařízení vlády č. 101/2005 Sb. stanoví podrobnější požadavky na pracoviště a pracovní prostředí. "
        "Nařízení vlády č. 378/2001 Sb. řeší bezpečný provoz a používání strojů, technických zařízení, přístrojů a nářadí. "
        "Nařízení vlády č. 495/2001 Sb. upravuje poskytování osobních ochranných pracovních prostředků. "
        "Nařízení vlády č. 375/2017 Sb. stanoví požadavky na bezpečnostní značky, značení a signály. "
        "Nařízení vlády č. 362/2005 Sb. stanoví požadavky pro práce ve výškách a nad volnou hloubkou.",
    ),
    (
        "8.3 Vyhrazená technická zařízení a elektro práce",
        "Zákon č. 250/2021 Sb. upravuje bezpečnost práce v souvislosti s provozem vyhrazených technických zařízení. "
        "Pro elektrická zařízení jsou významná zejména nařízení vlády č. 190/2022 Sb. k vyhrazeným elektrickým zařízením "
        "a nařízení vlády č. 194/2022 Sb. k odborné způsobilosti v elektrotechnice. Práce na elektrickém zařízení smí "
        "provádět pouze osoby s odpovídající kvalifikací, oprávněním a stanoveným pracovním postupem.",
    ),
    (
        "8.4 Požární ochrana",
        "Zákon č. 133/1985 Sb., o požární ochraně, a vyhláška č. 246/2001 Sb., o požární prevenci, stanoví základní "
        "požadavky požární ochrany, dokumentaci, preventivní opatření, povinnosti při činnostech se zvýšeným požárním "
        "nebezpečím a požadavky na věcné prostředky požární ochrany. Horké práce, kouření a manipulace s otevřeným ohněm "
        "se smí provádět pouze podle místních pravidel a vydaného povolení.",
    ),
    (
        "8.5 Pracovní úrazy a mimořádné události",
        "Od 01.01.2026 je účinné nařízení vlády č. 322/2025 Sb., o povinnostech zaměstnavatele při pracovních úrazech, "
        "které nahradilo dřívější úpravu evidence a hlášení pracovních úrazů. Každý úraz, nebezpečnou situaci, požár, "
        "únik látky nebo poškození zařízení oznamte ihned odpovědné osobě objednatele i svému nadřízenému.",
    ),
]

TRAINING_SECTIONS.extend(LEGAL_SECTIONS)


def build_test_questions():
    randomized = []
    for question in QUESTIONS:
        option_pairs = list(enumerate(question["options"]))
        random.shuffle(option_pairs)
        randomized.append(
            {
                "text": question["text"],
                "options": [option for _, option in option_pairs],
                "answer": next(
                    index
                    for index, (original_index, _) in enumerate(option_pairs)
                    if original_index == question["answer"]
                ),
            }
        )
    random.shuffle(randomized)
    return randomized

QUESTIONS = [
    {
        "text": "Co má nový zaměstnanec udělat, pokud nerozumí pokynu nebo riziku práce?",
        "options": [
            "Zeptat se nadřízeného nebo školitele před zahájením práce",
            "Začít pracovat a dotazy vyřešit později",
            "Řídit se pouze tím, co mu poradí kolega",
        ],
        "answer": 0,
    },
    {
        "text": "Kdy smí zaměstnanec obsluhovat stroj nebo zařízení?",
        "options": [
            "Kdykoli je zařízení volné",
            "Pouze pokud byl zaškolen a má potřebné oprávnění",
            "Pokud už podobné zařízení viděl dříve",
        ],
        "answer": 1,
    },
    {
        "text": "Jak se zachovat při poškození osobního ochranného pracovního prostředku?",
        "options": [
            "Používat ho dál, pokud práce trvá krátce",
            "Opravit ho páskou a pokračovat",
            "Ihned ho vyměnit nebo nahlásit potřebu výměny nadřízenému",
        ],
        "answer": 2,
    },
    {
        "text": "Co platí pro únikové cesty a hasicí přístroje?",
        "options": [
            "Musí zůstat volné a přístupné",
            "Mohou se dočasně zastavět materiálem",
            "Řeší se pouze při kontrole hasičů",
        ],
        "answer": 0,
    },
    {
        "text": "Kdy je dovoleno vyřadit ochranný kryt nebo bezpečnostní zařízení?",
        "options": [
            "Kdykoli zdržuje práci",
            "Pouze na vlastní odpovědnost zaměstnance",
            "Nikdy bez stanoveného postupu a povolení odpovědné osoby",
        ],
        "answer": 2,
    },
    {
        "text": "Co má zaměstnanec udělat při úrazu, téměř nehodě nebo nebezpečné situaci?",
        "options": [
            "Ihned událost oznámit nadřízenému nebo odpovědné osobě",
            "Vyčkat do konce směny",
            "Řešit pouze tehdy, když vznikla škoda",
        ],
        "answer": 0,
    },
    {
        "text": "Které číslo lze volat při ohrožení života, požáru nebo vážné nehodě?",
        "options": ["112", "1188", "12345"],
        "answer": 0,
    },
    {
        "text": "Jak má zaměstnanec zacházet s hesly a přístupovými údaji?",
        "options": [
            "Může je sdílet s kolegou, pokud spěchá",
            "Nesmí je sdílet a musí chránit přístup k firemním systémům",
            "Stačí je mít napsané u počítače",
        ],
        "answer": 1,
    },
    {
        "text": "Co platí pro kouření a otevřený oheň na pracovišti?",
        "options": [
            "Jsou dovolené všude venku",
            "Řídí se zákazy, povolenými místy a požárně bezpečnostními pravidly",
            "Jsou zakázané jen ve skladech",
        ],
        "answer": 1,
    },
    {
        "text": "Co je správný postup při podezřelém e-mailu nebo ztrátě firemního zařízení?",
        "options": [
            "Neprodleně to oznámit podle firemních pravidel",
            "Počkat, jestli se problém vyřeší sám",
            "Přeposlat e-mail dalším kolegům k posouzení",
        ],
        "answer": 0,
    },
]


def _content_payload():
    return {
        "training_sections": [{"title": title, "text": text} for title, text in TRAINING_SECTIONS],
        "questions": QUESTIONS,
    }


def save_training_sections(sections):
    global TRAINING_SECTIONS
    TRAINING_SECTIONS = [(str(title), str(text)) for title, text in sections]
    _ensure_content_file()
    try:
        payload = json.loads(TRAINING_CONTENT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    payload["training_sections"] = [
        {"title": title, "text": text}
        for title, text in TRAINING_SECTIONS
    ]
    payload.setdefault("questions", QUESTIONS)
    TRAINING_CONTENT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_content_file():
    if TRAINING_CONTENT_FILE.exists():
        return
    TRAINING_CONTENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_CONTENT_FILE.write_text(json.dumps(_content_payload(), ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_training_content_file():
    _ensure_content_file()
    return TRAINING_CONTENT_FILE


def _load_content_file():
    global TRAINING_SECTIONS, QUESTIONS
    _ensure_content_file()
    try:
        payload = json.loads(TRAINING_CONTENT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    sections = payload.get("training_sections")
    questions = payload.get("questions")
    if isinstance(sections, list):
        loaded_sections = []
        for section in sections:
            if isinstance(section, dict):
                loaded_sections.append((str(section.get("title", "")), str(section.get("text", ""))))
        if loaded_sections:
            TRAINING_SECTIONS = loaded_sections
    if isinstance(questions, list) and questions:
        loaded_questions = []
        for question in questions:
            if not isinstance(question, dict):
                continue
            options = question.get("options")
            answer = question.get("answer")
            if not isinstance(options, list) or not options:
                continue
            if not isinstance(answer, int) or answer < 0 or answer >= len(options):
                continue
            loaded_questions.append(
                {
                    "text": str(question.get("text", "")),
                    "options": [str(option) for option in options],
                    "answer": answer,
                }
            )
        if loaded_questions:
            QUESTIONS = loaded_questions


_load_content_file()
