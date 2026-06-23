# -*- coding: utf-8 -*-

import json
import random

from .bozppo_config import TRAINING_CONTENT_FILE

TRAINING_SECTIONS = [
    (
        "1. Bezpečnost práce",
        "",
    ),
    (
        "1.1 Povinnosti před zahájením pracovní činnosti",
        "Zpracovat zápis o předání a převzetí pracoviště (nutno uvést všechny známé skutečnosti, "
        "jež jsou významné z hlediska zajištění BOZP fyzických osob zdržujících se na pracovišti "
        "objednatele).",
    ),
    (
        "1. Úvod a odpovědnost",
        "Školení je určeno pro pracovníky externích firem před vstupem na pracoviště. "
        "Každý pracovník je povinen dodržovat pokyny objednatele, místní provozní řády, "
        "bezpečnostní značení a pokyny odpovědné osoby. Pracovník smí vykonávat pouze práce, "
        "ke kterým má kvalifikaci, oprávnění a souhlas odpovědné osoby.",
    ),
    (
        "2. Pohyb po pracovišti",
        "Po areálu se pohybujte pouze po vyznačených trasách a v povolených prostorech. "
        "Nevstupujte do technologických prostorů, skladů, rozvoden, strojoven a uzavřených "
        "pracovišť bez povolení. Dbejte na provoz manipulační techniky, vozidel a jeřábů. "
        "Zakázáno je obcházet nebo vyřazovat ochranná zařízení.",
    ),
    (
        "3. Osobní ochranné pracovní prostředky",
        "Používejte předepsané OOPP podle rizik dané práce: ochrannou přilbu, brýle, rukavice, "
        "pracovní obuv, reflexní vestu, ochranu sluchu nebo dýchacích cest. OOPP musí být "
        "funkční, čisté a správně nasazené. Poškozené OOPP ihned vyměňte.",
    ),
    (
        "4. Rizikové práce",
        "Práce ve výškách, práce s otevřeným ohněm, vstup do omezených prostorů, práce na "
        "elektrickém zařízení, manipulace s chemikáliemi a zdvihání břemen vyžadují zvláštní "
        "povolení, kvalifikaci a stanovení bezpečného postupu. Před zahájením práce ověřte "
        "rizika, zajištění pracoviště a kontakt na odpovědnou osobu.",
    ),
    (
        "5. Požární ochrana",
        "Dodržujte zákaz kouření a zákaz manipulace s otevřeným ohněm mimo povolená místa. "
        "Hořlaviny skladujte pouze v určených obalech a množství. Udržujte volné únikové cesty, "
        "hasicí přístroje a hydranty. Při práci s možností vzniku požáru musí být určena "
        "preventivní opatření a hasicí prostředky.",
    ),
    (
        "6. Mimořádné události a první pomoc",
        "Každý úraz, nebezpečnou situaci, požár, únik látky nebo poškození zařízení ihned oznamte "
        "odpovědné osobě. Při požáru varujte osoby v okolí, volejte pomoc, pokud je to bezpečné, "
        "použijte hasicí přístroj a řiďte se evakuačními pokyny. První pomoc poskytujte podle "
        "svých schopností a volejte 155 nebo 112.",
    ),
]


LEGAL_SECTIONS = [
    (
        "7. Aktuální právní předpisy BOZP a PO",
        "Přehled je informativní a je určen pro základní orientaci pracovníků externích firem. "
        "Vždy se řiďte aktuálním zněním právních předpisů, místní dokumentací objednatele, pokyny odpovědné osoby "
        "a konkrétním předáním pracoviště. Ověřeno k 17.05.2026.",
    ),
    (
        "7.1 Základní předpisy BOZP",
        "Zákon č. 262/2006 Sb., zákoník práce, zejména část věnovaná bezpečnosti a ochraně zdraví při práci, "
        "upravuje prevenci rizik, školení zaměstnanců, poskytování OOPP, povinnosti zaměstnavatele i povinnosti "
        "zaměstnanců. Zákon č. 309/2006 Sb. doplňuje požadavky na pracoviště, pracovní prostředí, bezpečnostní značky, "
        "prevenci rizik a některé povinnosti při stavebních a dalších rizikových činnostech.",
    ),
    (
        "7.2 Pracoviště, zařízení, OOPP a značení",
        "Nařízení vlády č. 101/2005 Sb. stanoví podrobnější požadavky na pracoviště a pracovní prostředí. "
        "Nařízení vlády č. 378/2001 Sb. řeší bezpečný provoz a používání strojů, technických zařízení, přístrojů a nářadí. "
        "Nařízení vlády č. 495/2001 Sb. upravuje poskytování osobních ochranných pracovních prostředků. "
        "Nařízení vlády č. 375/2017 Sb. stanoví požadavky na bezpečnostní značky, značení a signály. "
        "Nařízení vlády č. 362/2005 Sb. stanoví požadavky pro práce ve výškách a nad volnou hloubkou.",
    ),
    (
        "7.3 Vyhrazená technická zařízení a elektro práce",
        "Zákon č. 250/2021 Sb. upravuje bezpečnost práce v souvislosti s provozem vyhrazených technických zařízení. "
        "Pro elektrická zařízení jsou významná zejména nařízení vlády č. 190/2022 Sb. k vyhrazeným elektrickým zařízením "
        "a nařízení vlády č. 194/2022 Sb. k odborné způsobilosti v elektrotechnice. Práce na elektrickém zařízení smí "
        "provádět pouze osoby s odpovídající kvalifikací, oprávněním a stanoveným pracovním postupem.",
    ),
    (
        "7.4 Požární ochrana",
        "Zákon č. 133/1985 Sb., o požární ochraně, a vyhláška č. 246/2001 Sb., o požární prevenci, stanoví základní "
        "požadavky požární ochrany, dokumentaci, preventivní opatření, povinnosti při činnostech se zvýšeným požárním "
        "nebezpečím a požadavky na věcné prostředky požární ochrany. Horké práce, kouření a manipulace s otevřeným ohněm "
        "se smí provádět pouze podle místních pravidel a vydaného povolení.",
    ),
    (
        "7.5 Pracovní úrazy a mimořádné události",
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
        "text": "Kde se smí pracovník externí firmy pohybovat?",
        "options": [
            "Pouze v povolených prostorech a po určených trasách",
            "Kdekoli v areálu, pokud nikoho neruší",
            "Jen tam, kde nejsou kamery",
        ],
        "answer": 0,
    },
    {
        "text": "Co je nutné udělat před rizikovou prací, např. prací ve výškách nebo s otevřeným ohněm?",
        "options": [
            "Zahájit práci a povolení doplnit později",
            "Ověřit povolení, kvalifikaci, rizika a bezpečný postup",
            "Spoléhat se pouze na zkušenost pracovníka",
        ],
        "answer": 1,
    },
    {
        "text": "Jak se zachovat při poškození osobního ochranného prostředku?",
        "options": [
            "Používat ho dál, pokud práce trvá krátce",
            "Opravit ho páskou a pokračovat",
            "Ihned ho vyměnit nebo nahlásit potřebu výměny",
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
        "text": "Kdy je dovoleno vyřadit ochranný kryt nebo bezpečnostní zařízení stroje?",
        "options": [
            "Kdykoli zdržuje práci",
            "Pouze na vlastní odpovědnost pracovníka",
            "Nikdy bez stanoveného postupu a povolení odpovědné osoby",
        ],
        "answer": 2,
    },
    {
        "text": "Co má pracovník udělat při úrazu nebo nebezpečné situaci?",
        "options": [
            "Ihned událost oznámit odpovědné osobě",
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
        "text": "Kdo smí vykonávat práci na elektrickém zařízení?",
        "options": [
            "Každý pracovník externí firmy",
            "Pouze osoba s příslušnou kvalifikací a povolením",
            "Kdokoli, pokud je zařízení vypnuté",
        ],
        "answer": 1,
    },
    {
        "text": "Co platí pro kouření a otevřený oheň v areálu?",
        "options": [
            "Jsou dovolené všude venku",
            "Řídí se zákazy, povolenými místy a požárně bezpečnostními pravidly",
            "Jsou zakázané jen ve skladech",
        ],
        "answer": 1,
    },
    {
        "text": "Jak má pracovník postupovat, pokud nerozumí pokynu nebo riziku práce?",
        "options": [
            "Začít pracovat pomalu a opatrně",
            "Zeptat se odpovědné osoby před zahájením práce",
            "Požádat kolegu, aby rozhodl za něj",
        ],
        "answer": 1,
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
