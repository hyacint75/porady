# -*- coding: utf-8 -*-


HANDOVER_TEMPLATES = {
    "Obecné práce": {
        "scope": "Běžné servisní, kontrolní nebo pomocné práce dle objednávky.",
        "risks": "Pohyb osob a vozidel, manipulace s materiálem, zakopnutí, uklouznutí, hluk, prach.",
        "measures": "Dodržovat pokyny odpovědné osoby, používat předepsané OOPP, udržovat pořádek, nezastavovat únikové cesty.",
        "fire": "Dodržovat zákaz kouření a manipulace s otevřeným ohněm mimo povolená místa.",
        "docs": "Seznámení s místními pravidly BOZP a PO, předání kontaktu na odpovědnou osobu.",
        "pictograms": ["VAROVÁNÍ", "OOPP", "POHYB"],
    },
    "Montážní práce": {
        "scope": "Montáž, demontáž nebo úprava zařízení a konstrukčních prvků.",
        "risks": "Manipulace s břemeny, práce s ručním nářadím, ostré hrany, pád materiálu, pohyb manipulační techniky.",
        "measures": "Používat ochrannou obuv, rukavice, brýle a přilbu dle místa práce. Zajistit pracovní prostor proti vstupu nepovolaných osob.",
        "fire": "Hořlavé materiály ukládat mimo zdroje tepla. Horké práce provádět pouze s povolením.",
        "docs": "Pracovní postup, návody k zařízení, potřebná oprávnění obsluhy.",
        "pictograms": ["VAROVÁNÍ", "PÁD PŘEDMĚTU", "OOPP", "BŘEMENA"],
    },
    "Elektro práce": {
        "scope": "Práce na elektrickém zařízení, kontrola, servis nebo zapojení elektroinstalace.",
        "risks": "Úraz elektrickým proudem, oblouk, záměna obvodů, práce v blízkosti živých částí.",
        "measures": "Práce smí provádět pouze osoba s příslušnou kvalifikací. Zajistit vypnutí, ověření beznapěťového stavu a označení pracoviště.",
        "fire": "Zajistit dostupnost hasicího prostředku vhodného pro elektrozařízení. Nepoužívat vodu na zařízení pod napětím.",
        "docs": "Doklad o kvalifikaci, pracovní povolení, schéma zapojení, záznam o zajištění zařízení.",
        "pictograms": ["ELEKTRO", "ZÁKAZ VSTUPU", "OOPP", "HASIVO"],
    },
    "Práce ve výškách": {
        "scope": "Práce na žebříku, lešení, plošině nebo v místě s rizikem pádu.",
        "risks": "Pád osob, pád předmětů, nestabilní podklad, nepříznivé počasí, kontakt s technologií.",
        "measures": "Používat prostředky proti pádu, bezpečné žebříky nebo plošiny, vymezit prostor pod prací a kontrolovat stav pracoviště.",
        "fire": "Bez zvláštních požárních rizik, pokud nejsou současně prováděny horké práce.",
        "docs": "Oprávnění pro práci ve výškách, kontrola lešení nebo plošiny, pracovní postup.",
        "pictograms": ["PÁD OSOB", "PÁD PŘEDMĚTU", "OOPP", "ZÁBRANA"],
    },
    "Svařování / horké práce": {
        "scope": "Svařování, broušení, řezání, pálení nebo jiné práce se vznikem tepla a jisker.",
        "risks": "Vznik požáru, popálení, záření, dým, jiskry, tlakové lahve, hořlavé materiály v okolí.",
        "measures": "Odstranit nebo zakrýt hořlavé materiály, zajistit větrání, používat štít, rukavice a ochranný oděv.",
        "fire": "Provádět pouze na povolení k horkým pracím. Mít připravený hasicí přístroj a zajistit požární dohled po skončení práce.",
        "docs": "Povolení k horkým pracím, doklad kvalifikace svářeče, kontrola tlakových lahví.",
        "pictograms": ["POŽÁR", "HORKÉ PRÁCE", "OOPP", "TLAKOVÉ LAHVE"],
    },
    "Servis technologie": {
        "scope": "Servis, kontrola nebo seřízení výrobního či technologického zařízení.",
        "risks": "Neočekávané spuštění stroje, pohyblivé části, tlaková nebo hydraulická energie, hluk, únik látek.",
        "measures": "Zajistit zařízení proti spuštění, vyvěsit označení, dohodnout odpovědnou osobu a dodržet bezpečný pracovní postup.",
        "fire": "Zkontrolovat, zda servis nevyvolává požární riziko. Hořlavé látky skladovat jen v nezbytném množství.",
        "docs": "Servisní postup, návod výrobce, předávací protokol, případná povolení k odstávce.",
        "pictograms": ["STROJ", "UZAMKNOUT", "OOPP", "HLUK"],
    },
}
