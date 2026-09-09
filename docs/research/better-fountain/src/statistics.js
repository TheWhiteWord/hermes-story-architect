"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.retrieveScreenPlayStatistics = void 0;
const afterwriting_parser_1 = require("./afterwriting-parser");
const pdf_1 = require("./pdf/pdf");
const utils_1 = require("./utils");
const readabilityScores = require("readability-scores");
function age(value) {
    var max = 22;
    return value > max ? max : value;
}
function gradeToAge(grade) {
    return age(Math.round(grade + 5));
}
const createCharacterStatistics = (parsed) => {
    const dialoguePieces = [];
    for (var i = 0; i < parsed.tokens.length; i++) {
        while (i < parsed.tokens.length && parsed.tokens[i].type === "character") {
            const character = parsed.tokens[i].name();
            var speech = "";
            while (i++ && i < parsed.tokens.length) {
                if (parsed.tokens[i].type === "dialogue") {
                    speech += parsed.tokens[i].text + " ";
                }
                else if (parsed.tokens[i].type === "character") {
                    break;
                }
                // else skip extensions / parenthesis / dialogue-begin/-end
            }
            speech = speech.trim();
            dialoguePieces.push({
                character,
                speech
            });
        }
    }
    const dialoguePerCharacter = {};
    dialoguePieces.forEach((dialoguePiece) => {
        if (dialoguePerCharacter.hasOwnProperty(dialoguePiece.character)) {
            dialoguePerCharacter[dialoguePiece.character].push(dialoguePiece.speech);
        }
        else {
            dialoguePerCharacter[dialoguePiece.character] = [dialoguePiece.speech];
        }
    });
    const characterStats = [];
    let speechcomplexityArray = [];
    let monologueCounter = 0;
    Object.keys(dialoguePerCharacter).forEach((singledialPerChar) => {
        const speakingParts = dialoguePerCharacter[singledialPerChar].length;
        let averageComplexity = 0;
        let secondsSpoken = 0;
        let monologues = 0;
        let combinedSentences = "";
        const allDialogueCombined = dialoguePerCharacter[singledialPerChar].reduce((prev, curr) => {
            let time = (0, utils_1.calculateDialogueDuration)(curr);
            secondsSpoken += time;
            combinedSentences += "." + curr;
            if ((0, utils_1.isMonologue)(time))
                monologues++;
            return `${prev} ${curr} `;
        }, "");
        monologueCounter += monologues;
        var readability = readabilityScores(combinedSentences);
        if (readability) {
            averageComplexity = (gradeToAge(readability.daleChall) +
                gradeToAge(readability.ari) +
                gradeToAge(readability.colemanLiau) +
                gradeToAge(readability.fleschKincaid) +
                gradeToAge(readability.smog) +
                gradeToAge(readability.gunningFog)) / 6;
            if (averageComplexity > 0)
                speechcomplexityArray.push(averageComplexity);
        }
        const wordsSpoken = getWordCount(allDialogueCombined);
        characterStats.push({
            name: singledialPerChar,
            color: (0, utils_1.rgbToHex)((0, utils_1.wordToColor)(singledialPerChar, 0.6, 0.5)),
            speakingParts,
            secondsSpoken,
            averageComplexity,
            monologues,
            wordsSpoken,
        });
    });
    characterStats.sort((a, b) => {
        // by parts
        if (b.speakingParts > a.speakingParts)
            return +1;
        if (b.speakingParts < a.speakingParts)
            return -1;
        // then by words
        if (b.wordsSpoken > a.wordsSpoken)
            return +1;
        if (b.wordsSpoken < a.wordsSpoken)
            return -1;
        return 0;
    });
    return {
        characters: characterStats,
        complexity: (0, utils_1.median)(speechcomplexityArray),
        characterCount: characterStats.length,
        monologues: monologueCounter
    };
};
const createLocationStatistics = (parsed) => {
    const locationSlugs = [...parsed.properties.locations.keys()];
    return {
        locationsCount: locationSlugs.length,
        locations: locationSlugs.map((location_slug) => {
            const references = parsed.properties.locations.get(location_slug);
            const times_of_day = references
                .map(it => locationtime(it.time_of_day))
                .filter((v, i, a) => a.indexOf(v) === i);
            const interior = references.some(it => it.interior);
            const exterior = references.some(it => it.exterior);
            let interior_exterior = 'other';
            if (interior && exterior)
                interior_exterior = 'mixed';
            else if (interior)
                interior_exterior = 'int';
            else if (exterior)
                interior_exterior = 'ext';
            return {
                color: (0, utils_1.rgbToHex)((0, utils_1.wordToColor)(location_slug)),
                name: references[0].name,
                scene_numbers: references.map(reference => reference.scene_number),
                scene_lines: references.map(reference => reference.line),
                number_of_scenes: references.length,
                times_of_day,
                interior_exterior
            };
        })
    };
};
const createSceneStatistics = (parsed) => {
    const sceneStats = [];
    parsed.tokens.forEach((tok) => {
        if (tok.type === "scene_heading") {
            sceneStats.push({
                title: tok.text
            });
        }
    });
    return {
        scenes: sceneStats,
    };
};
function locationtype(val) {
    if (val) {
        if (/i(nt)?\.?\/e(xt)?\.?/i.test(val)) {
            return "mixed";
        }
        else if (/i(nt)?\.?/i.test(val)) {
            return "int";
        }
        else if (/e(xt)?\.?/i.test(val)) {
            return "ext";
        }
    }
    return "other";
}
function afterdash(val) {
    if (val) {
        let dash = val.lastIndexOf(" - ");
        if (dash === -1)
            dash = val.lastIndexOf(" – ");
        if (dash === -1)
            dash = val.lastIndexOf(" — ");
        if (dash === -1)
            dash = val.lastIndexOf(" − ");
        if (dash !== -1) {
            return val.substring(dash + 3);
        }
    }
    return null;
}
function locationtime(val) {
    if (val) {
        return val.toLowerCase()
            .replace(/\s+/g, ' ')
            .replace(/\.$/g, '')
            .replace(/[^\w ]+/g, '')
            .replace(/  +/g, ' ')
            .trim()
            .replace(/^(the)?\s*(next|following)\b/i, '')
            .replace(/^(early|late)\b/i, '')
            .trim();
    }
    return "unspecified";
}
const getLengthChart = (parsed) => {
    let action = [{ line: 0, length: 0, scene: undefined }];
    let dialogue = [{ line: 0, length: 0, scene: undefined }];
    let characters = new Map();
    let scenes = [];
    let previousLengthAction = 0;
    let previousLengthDialogue = 0;
    let currentScene = "";
    let monologues = 0;
    let scenepropDurations = new Map();
    parsed.tokens.forEach(element => {
        if (element.type == "action" || element.type == "dialogue") {
            let time = Number(element.time);
            if (!isNaN(time)) {
                if (element.type == "action") {
                    previousLengthAction += Number(element.time);
                }
                else if (element.type == "dialogue") {
                    previousLengthDialogue += Number(element.time);
                }
            }
            if (element.type == "action") {
                action.push({ line: element.line, length: previousLengthAction, scene: currentScene });
            }
            else if (element.type == "dialogue") {
                dialogue.push({ line: element.line, length: previousLengthDialogue, scene: currentScene });
                let currentCharacter = characters.get(element.character);
                let dialogueLength = 0;
                let wordsLength = 0;
                let wordcount = getWordCount(element.text);
                let time = Number(element.time);
                if (!currentCharacter) {
                    characters.set(element.character, []);
                }
                else if (currentCharacter.length > 0) {
                    dialogueLength = currentCharacter[currentCharacter.length - 1].lengthTimeGlobal;
                    wordsLength = currentCharacter[currentCharacter.length - 1].lengthWordsGlobal;
                }
                let monologue = false;
                if ((0, utils_1.isMonologue)(time)) {
                    monologue = true;
                    monologues++;
                }
                characters.get(element.character).push({
                    line: element.line,
                    lengthTime: element.time,
                    lengthWords: wordcount,
                    lengthTimeGlobal: dialogueLength + time,
                    lengthWordsGlobal: wordsLength + wordcount,
                    monologue: monologue,
                    scene: currentScene,
                });
            }
        }
    });
    parsed.properties.scenes.forEach(scene => {
        currentScene = scene.text;
        if (scenes.length > 0) {
            scenes[scenes.length - 1].endline = scene.line - 1;
        }
        var deconstructedSlug = afterwriting_parser_1.regex.scene_heading.exec(scene.text);
        const sceneType = locationtype(deconstructedSlug === null || deconstructedSlug === void 0 ? void 0 : deconstructedSlug[1]);
        const sceneTime = locationtime(afterdash(deconstructedSlug === null || deconstructedSlug === void 0 ? void 0 : deconstructedSlug[2]));
        scenes.push({
            type: sceneType,
            line: scene.line,
            endline: 65500,
            time: sceneTime,
            scene: scene.text
        });
        let currentLength = scenepropDurations.has('type_' + sceneType) ? scenepropDurations.get('type_' + sceneType) : 0;
        scenepropDurations.set('type_' + sceneType, currentLength + scene.actionLength + scene.dialogueLength);
        currentLength = scenepropDurations.has('time_' + sceneTime) ? scenepropDurations.get('time_' + sceneTime) : 0;
        scenepropDurations.set('time_' + sceneTime, currentLength + scene.actionLength + scene.dialogueLength);
    });
    let characterDuration = [];
    let characterNames = [];
    characters.forEach((value, key) => {
        characterNames.push(key);
        characterDuration.push(value);
    });
    return { action: action, dialogue: dialogue, durationByProp: (0, utils_1.mapToObject)(scenepropDurations), scenes: scenes, characters: characterDuration, characternames: characterNames, monologues: monologues };
};
const getWordCount = (script) => {
    return ((script || '').match(/\S+/g) || []).length;
};
const getCharacterCount = (script) => {
    return script.length;
};
const getCharacterCountWithoutWhitespace = (script) => {
    return ((script || '').match(/\S+?/g) || []).length;
};
const getLineCount = (script) => {
    return ((script || '').match(/\n/g) || []).length;
};
const getLineCountWithoutWhitespace = (script) => {
    return ((script || '').match(/^.*\S.*$/gm) || []).length;
};
const createLengthStatistics = (script, pdf, parsed) => {
    return {
        characters: getCharacterCount(script),
        characterswithoutwhitespace: getCharacterCountWithoutWhitespace(script),
        lines: getLineCount(script),
        lineswithoutwhitespace: getLineCountWithoutWhitespace(script),
        words: getWordCount(script),
        pagesreal: pdf.pagecountReal,
        pages: pdf.pagecount,
        scenes: parsed.properties.scenes.length
    };
};
const createDurationStatistics = (parsed) => {
    let lengthcharts = getLengthChart(parsed);
    return {
        dialogue: parsed.lengthDialogue,
        action: parsed.lengthAction,
        total: parsed.lengthDialogue + parsed.lengthAction,
        durationBySceneProp: lengthcharts.durationByProp,
        lengthchart_action: lengthcharts.action,
        lengthchart_dialogue: lengthcharts.dialogue,
        characters: lengthcharts.characters,
        scenes: lengthcharts.scenes,
        characternames: lengthcharts.characternames,
        monologues: lengthcharts.monologues
    };
};
const retrieveScreenPlayStatistics = (script, parsed, config, exportconfig) => __awaiter(void 0, void 0, void 0, function* () {
    const stats = {
        characterStats: createCharacterStatistics(parsed),
        sceneStats: createSceneStatistics(parsed),
        locationStats: createLocationStatistics(parsed),
        durationStats: createDurationStatistics(parsed),
        structure: parsed.properties.structure
    };
    let pdfstats = yield (0, pdf_1.GeneratePdf)("$STATS$", config, exportconfig, parsed, undefined);
    let pdfmap = (0, utils_1.mapToObject)(pdfstats.linemap);
    return Object.assign(Object.assign({}, stats), { lengthStats: createLengthStatistics(script, pdfstats, parsed), pdfmap: JSON.stringify(pdfmap) });
});
exports.retrieveScreenPlayStatistics = retrieveScreenPlayStatistics;
//# sourceMappingURL=statistics.js.map