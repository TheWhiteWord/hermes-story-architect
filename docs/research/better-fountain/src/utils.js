"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.median = exports.rgbToHex = exports.mapToObject = exports.getAssetsUri = exports.resolveAsUri = exports.wordToColor = exports.getPackageInfo = exports.assetsPath = exports.revealFile = exports.openFile = exports.fileToBase64 = exports.last = exports.shiftScenes = exports.updateSceneNumbers = exports.overwriteSceneNumbers = exports.secondsToMinutesString = exports.secondsToString = exports.isMonologue = exports.calculateDialogueDuration = exports.findCharacterThatSpokeBeforeTheLast = exports.getCharactersWhoSpokeBeforeLast = exports.addForceSymbolToCharacter = exports.trimCharacterForceSymbol = exports.parseLocationInformation = exports.trimCharacterExtension = exports.slugify = exports.getEditor = exports.getActiveFountainDocument = void 0;
const vscode = require("vscode");
const Preview_1 = require("./providers/Preview");
const parser = require("./afterwriting-parser");
const path = require("path");
const telemetry = require("./telemetry");
const sceneNumbering = require("./scenenumbering");
const fs = require("fs");
/**
 * @returns {vscode.Uri} relevant fountain document for the currently selected preview or text editor
 */
function getActiveFountainDocument() {
    //first check if any previews have focus
    for (let i = 0; i < Preview_1.previews.length; i++) {
        if (Preview_1.previews[i].panel.active)
            return vscode.Uri.parse(Preview_1.previews[i].uri);
    }
    //no previews were active, is activeTextEditor a fountain document?
    if (vscode.window.activeTextEditor != undefined && vscode.window.activeTextEditor.document.languageId == "fountain") {
        return vscode.window.activeTextEditor.document.uri;
    }
    //As a last resort, check if there are any visible fountain text editors
    for (let i = 0; i < vscode.window.visibleTextEditors.length; i++) {
        if (vscode.window.visibleTextEditors[i].document.languageId == "fountain")
            return vscode.window.visibleTextEditors[i].document.uri;
    }
    //all hope is lost
    return undefined;
}
exports.getActiveFountainDocument = getActiveFountainDocument;
/**
 * @param uri the uri of the fountain document to search for
 * @returns the editor that is currently displaying the fountain document with the given uri
 */
function getEditor(uri) {
    //search visible text editors
    for (let i = 0; i < vscode.window.visibleTextEditors.length; i++) {
        if (vscode.window.visibleTextEditors[i].document.uri.toString() == uri.toString())
            return vscode.window.visibleTextEditors[i];
    }
    //the editor was not visible,
    return undefined;
}
exports.getEditor = getEditor;
//var syllable = require('syllable');
function slugify(text) {
    return text.toString().toLowerCase()
        .replace(/\s+/g, '-') // Replace spaces with -
        .replace(/[^\w-]+/g, '') // Remove all non-word chars
        .replace(/-{2,}/g, '-') // Replace multiple - with single -
        .replace(/^-+/, '') // Trim - from start of text
        .replace(/-+$/, ''); // Trim - from end of text
}
exports.slugify = slugify;
/**
 * Trims character extensions, for example the parantheses part in `JOE (on the radio)`
 */
const trimCharacterExtension = (character) => character.replace(/[ \t]*(\(.*\))[ \t]*([ \t]*\^)?$/, "");
exports.trimCharacterExtension = trimCharacterExtension;
const parseLocationInformation = (scene_heading) => {
    //input group 1 is int/ext, group 2 is location and time, group 3 is scene number
    let splitLocationFromTime = scene_heading[2].match(/(.*)[-–—−](.*)/);
    if (scene_heading != null && scene_heading.length >= 3) {
        return {
            name: splitLocationFromTime ? splitLocationFromTime[1].trim() : scene_heading[2].trim(),
            interior: scene_heading[1].indexOf('I') != -1,
            exterior: scene_heading[1].indexOf('EX') != -1 || scene_heading[1].indexOf('E.') != -1,
            time_of_day: splitLocationFromTime ? splitLocationFromTime[2].trim() : ""
        };
    }
    return null;
};
exports.parseLocationInformation = parseLocationInformation;
/**
 * Trims the `@` symbol necessary in character names if they contain lower-case letters, i.e. `@McCONNOR`
 */
const trimCharacterForceSymbol = (character) => character.replace(/^[ \t]*@/, "");
exports.trimCharacterForceSymbol = trimCharacterForceSymbol;
/**
 * Character names containing lowercase letters need to be prefixed with an `@` symbol
 */
const addForceSymbolToCharacter = (characterName) => {
    const containsLowerCase = (text) => ((/[\p{Ll}]/u).test(text));
    return containsLowerCase(characterName) ? `@${characterName}` : characterName;
};
exports.addForceSymbolToCharacter = addForceSymbolToCharacter;
const getCharactersWhoSpokeBeforeLast = (parsedDocument, position) => {
    let searchIndex = 0;
    if (parsedDocument.tokenLines[position.line - 1]) {
        searchIndex = parsedDocument.tokenLines[position.line - 1];
    }
    let stopSearch = false;
    let previousCharacters = [];
    let lastCharacter = undefined;
    while (searchIndex > 0 && !stopSearch) {
        var token = parsedDocument.tokens[searchIndex - 1];
        if (token.type == "character") {
            var name = (0, exports.trimCharacterForceSymbol)((0, exports.trimCharacterExtension)(token.text)).trim();
            if (lastCharacter == undefined) {
                lastCharacter = name;
            }
            else if (name != lastCharacter && previousCharacters.indexOf(name) == -1) {
                previousCharacters.push(name);
            }
        }
        else if (token.type == "scene_heading") {
            stopSearch = true;
        }
        searchIndex--;
    }
    if (lastCharacter != undefined)
        previousCharacters.push(lastCharacter);
    return previousCharacters;
};
exports.getCharactersWhoSpokeBeforeLast = getCharactersWhoSpokeBeforeLast;
const findCharacterThatSpokeBeforeTheLast = (document, position, fountainDocProps) => {
    const isAlreadyMentionedCharacter = (text) => fountainDocProps.characters.has(text);
    let characterBeforeLast = "";
    let lineToInspect = 1;
    let foundLastCharacter = false;
    do {
        const beginningOfLineToInspect = new vscode.Position(position.line - lineToInspect, 0);
        const endOfLineToInspect = new vscode.Position(position.line - (lineToInspect - 1), 0);
        let potentialCharacterLine = document.getText(new vscode.Range(beginningOfLineToInspect, endOfLineToInspect)).trimRight();
        potentialCharacterLine = (0, exports.trimCharacterExtension)(potentialCharacterLine);
        potentialCharacterLine = (0, exports.trimCharacterForceSymbol)(potentialCharacterLine);
        if (isAlreadyMentionedCharacter(potentialCharacterLine)) {
            if (foundLastCharacter) {
                characterBeforeLast = potentialCharacterLine;
            }
            else {
                foundLastCharacter = true;
            }
        }
        lineToInspect++;
    } while (!characterBeforeLast);
    return characterBeforeLast;
};
exports.findCharacterThatSpokeBeforeTheLast = findCharacterThatSpokeBeforeTheLast;
/**
 * Calculate an approximation of how long a line of dialogue would take to say
 */
const calculateDialogueDuration = (dialogue) => {
    var duration = 0;
    //According to this paper: http://www.office.usp.ac.jp/~klinger.w/2010-An-Analysis-of-Articulation-Rates-in-Movies.pdf
    //The average amount of syllables per second in the 14 movies analysed is 5.13994 (0.1945548s/syllable)
    var sanitized = dialogue.replace(/[^\w]/gi, '');
    duration += ((sanitized.length) / 3) * 0.1945548;
    //duration += syllable(dialogue)*0.1945548;
    //According to a very crude analysis involving watching random movie scenes on youtube and measuring pauses with a stopwatch
    //A comma in the middle of a sentence adds 0.4sec and a full stop/excalmation/question mark adds 0.8 sec.
    var punctuationMatches = dialogue.match(/(\.|\?|\!|\:) |(\, )/g);
    if (punctuationMatches) {
        if (punctuationMatches[0])
            duration += 0.75 * punctuationMatches[0].length;
        if (punctuationMatches[1])
            duration += 0.3 * punctuationMatches[1].length;
    }
    return duration;
};
exports.calculateDialogueDuration = calculateDialogueDuration;
const isMonologue = (seconds) => {
    if (seconds > 30)
        return true;
    else
        return false;
};
exports.isMonologue = isMonologue;
function padZero(i) {
    if (i < 10) {
        i = "0" + i;
    }
    return i;
}
function secondsToString(seconds) {
    var time = new Date(null);
    time.setHours(0);
    time.setMinutes(0);
    time.setSeconds(seconds);
    return padZero(time.getHours()) + ":" + padZero(time.getMinutes()) + ":" + padZero(time.getSeconds());
}
exports.secondsToString = secondsToString;
function secondsToMinutesString(seconds) {
    if (seconds < 1)
        return undefined;
    var time = new Date(null);
    time.setHours(0);
    time.setMinutes(0);
    time.setSeconds(seconds);
    if (seconds >= 3600)
        return padZero(time.getHours()) + ":" + padZero(time.getMinutes()) + ":" + padZero(time.getSeconds());
    else
        return padZero(time.getHours() * 60 + time.getMinutes()) + ":" + padZero(time.getSeconds());
}
exports.secondsToMinutesString = secondsToMinutesString;
const overwriteSceneNumbers = () => {
    telemetry.reportTelemetry("command:fountain.overwriteSceneNumbers");
    const fullText = vscode.window.activeTextEditor.document.getText();
    const clearedText = clearSceneNumbers(fullText);
    writeSceneNumbers(clearedText);
    /* done like this because using vscode.window.activeTextEditor.edit()
     *  multiple times per callback is unpredictable; only writeSceneNumbers() does it
     */
};
exports.overwriteSceneNumbers = overwriteSceneNumbers;
const updateSceneNumbers = () => {
    telemetry.reportTelemetry("command:fountain.updateSceneNumbers");
    const fullText = vscode.window.activeTextEditor.document.getText();
    writeSceneNumbers(fullText);
};
exports.updateSceneNumbers = updateSceneNumbers;
const clearSceneNumbers = (fullText) => {
    const regexSceneHeadings = new RegExp(parser.regex.scene_heading.source, "igm");
    const newText = fullText.replace(regexSceneHeadings, (heading) => heading.replace(/ #.*#$/, ""));
    return newText;
};
// rewrites/updates Scene Numbers using the configured Numbering Schema (currently only 'Standard', not yet configurable)
const writeSceneNumbers = (fullText) => {
    // collect existing numbers (they mostly shouldn't change)
    const oldNumbers = [];
    const regexSceneHeadings = new RegExp(parser.regex.scene_heading.source, "igm");
    const numberingSchema = sceneNumbering.makeSceneNumberingSchema(sceneNumbering.SceneNumberingSchemas.Standard);
    var m;
    while (m = regexSceneHeadings.exec(fullText)) {
        const matchExisting = m[0].match(/#(.+)#$/);
        if (!matchExisting)
            oldNumbers.push(null); /* no match = no number = new number required in this slot */
        else if (numberingSchema.canParse(matchExisting[1]))
            oldNumbers.push(matchExisting[1]); /* existing scene number */
        /* ELSE: didn't parse - custom scene numbers are skipped */
    }
    // work out what they should actually be, according to the schema
    const newNumbers = sceneNumbering.generateSceneNumbers(oldNumbers);
    if (newNumbers) {
        // replace scene numbers
        const newText = fullText.replace(regexSceneHeadings, (heading) => {
            const matchExisting = heading.match(/#(.+)#$/);
            if (matchExisting && !numberingSchema.canParse(matchExisting[1]))
                return heading; /* skip re-writing custom scene numbers */
            const noPrevHeadingNumbers = heading.replace(/ #.+#$/, "");
            const newHeading = `${noPrevHeadingNumbers} #${newNumbers.shift()}#`;
            return newHeading;
        });
        vscode.window.activeTextEditor.edit(editBuilder => editBuilder.replace(new vscode.Range(new vscode.Position(0, 0), new vscode.Position(vscode.window.activeTextEditor.document.lineCount, 0)), newText));
    }
};
/** Shifts scene/s at the selected text up or down */
const shiftScenes = (editor, parsed, direction) => {
    var numNewlinesAtEndRequired = 0;
    const selectSceneAt = (sel) => {
        // returns range that contains whole scenes that overlap with the selection
        const headingsBefore = parsed.tokens
            .filter(token => (token.is("scene_heading") || token.is("section"))
            && token.line <= sel.active.line
            && token.line <= sel.anchor.line)
            .sort((a, b) => b.line - a.line);
        const headingsAfter = parsed.tokens
            .filter(token => (token.is("scene_heading") || token.is("section"))
            && token.line > sel.active.line
            && token.line > sel.anchor.line)
            .sort((a, b) => a.line - b.line);
        if (headingsBefore.length == 0)
            return null;
        const selStart = +headingsBefore[0].line;
        if (headingsAfter.length) {
            const selEnd = +headingsAfter[0].line;
            return new vscode.Selection(selStart, 0, selEnd, 0);
        }
        else {
            // +2 is where the next scene would start if there was one. done to make it look consistent.
            const selEnd = (0, exports.last)(parsed.tokens.filter(token => token.line)).line + 2;
            if (selEnd >= editor.document.lineCount)
                numNewlinesAtEndRequired = selEnd - editor.document.lineCount + 1;
            return new vscode.Selection(selStart, 0, selEnd, 0);
        }
    };
    // get range of scene/s that are shifting
    var moveSelection = selectSceneAt(editor.selection);
    if (moveSelection == null)
        return; // edge case: using command before the first scene
    var moveText = editor.document.getText(moveSelection) + (new Array(numNewlinesAtEndRequired + 1).join("\n"));
    numNewlinesAtEndRequired = 0;
    // get range of scene being swapped with selected scene/s
    var aboveSelection = (direction == -1) && selectSceneAt(new vscode.Selection(moveSelection.anchor.line - 1, 0, moveSelection.anchor.line - 1, 0));
    var belowSelection = (direction == 1) && selectSceneAt(new vscode.Selection(moveSelection.active.line + 1, 0, moveSelection.active.line + 1, 0));
    // edge cases: no scenes above or below to swap with
    if (!belowSelection && !aboveSelection)
        return;
    if (belowSelection && belowSelection.anchor.line < moveSelection.active.line)
        return;
    var reselectDelta = 0;
    const newLinePos = editor.document.lineAt(editor.document.lineCount - 1).range.end;
    editor.edit(editBuilder => {
        // going bottom-up to avoid re-aligning line numbers
        // might need empty lines at the bottom so the cut-paste behaves the same as if there were more scenes
        while (numNewlinesAtEndRequired) {
            // vscode makes this \r\n when appropriate
            editBuilder.insert(newLinePos, "\n");
            numNewlinesAtEndRequired--;
        }
        // paste below?
        if (belowSelection) {
            editBuilder.insert(new vscode.Position(belowSelection.active.line, 0), moveText);
            reselectDelta = belowSelection.active.line - belowSelection.anchor.line;
        }
        // delete original
        editBuilder.delete(moveSelection);
        // paste above?
        if (aboveSelection) {
            editBuilder.insert(new vscode.Position(aboveSelection.anchor.line, 0), moveText);
            reselectDelta = aboveSelection.anchor.line - moveSelection.anchor.line;
        }
    });
    // reselect any text that was originally selected / cursor position
    editor.selection = new vscode.Selection(editor.selection.anchor.translate(reselectDelta), editor.selection.active.translate(reselectDelta));
    editor.revealRange(editor.selection);
};
exports.shiftScenes = shiftScenes;
const last = function (array) {
    return array[array.length - 1];
};
exports.last = last;
function fileToBase64(fspath) {
    let data = fs.readFileSync(fspath);
    return data.toString('base64');
}
exports.fileToBase64 = fileToBase64;
function openFile(p) {
    let cmd = "xdg-open";
    switch (process.platform) {
        case 'darwin':
            cmd = 'open';
            break;
        case 'win32':
            cmd = '';
            break;
        default: cmd = 'xdg-open';
    }
    var exec = require('child_process').exec;
    exec(`${cmd} "${p}"`);
}
exports.openFile = openFile;
function revealFile(p) {
    var cmd = "";
    if (process.platform == "win32") {
        cmd = `explorer.exe /select,${p}`;
    }
    else if (process.platform == "darwin") {
        cmd = `open -r ${p}`;
    }
    else {
        p = path.parse(p).dir;
        cmd = `open "${p}"`;
    }
    var exec = require('child_process').exec;
    exec(cmd);
}
exports.revealFile = revealFile;
function assetsPath() {
    return __dirname;
}
exports.assetsPath = assetsPath;
function getPackageInfo() {
    const extension = vscode.extensions.getExtension('piersdeseilligny.betterfountain');
    if (extension && extension.packageJSON) {
        return {
            name: extension.packageJSON.name,
            version: extension.packageJSON.version,
            aiKey: extension.packageJSON.aiKey
        };
    }
    return null;
}
exports.getPackageInfo = getPackageInfo;
//Simple n-bit hash
function nPearsonHash(message, n = 8) {
    // Ideally, this table would be shuffled...
    // 256 will be the highest value provided by this hashing function
    var table = [...new Array(Math.pow(2, n))].map((_, i) => i);
    return message.split('').reduce((hash, c) => {
        return table[(hash + c.charCodeAt(0)) % (table.length - 1)];
    }, message.length % (table.length - 1));
}
function HSVToRGB(h, s, v) {
    var [r, g, b] = [0, 0, 0];
    var i = Math.floor(h * 6);
    var f = h * 6 - i;
    var p = v * (1 - s);
    var q = v * (1 - f * s);
    var t = v * (1 - (1 - f) * s);
    switch (i % 6) {
        case 0:
            r = v, g = t, b = p;
            break;
        case 1:
            r = q, g = v, b = p;
            break;
        case 2:
            r = p, g = v, b = t;
            break;
        case 3:
            r = p, g = q, b = v;
            break;
        case 4:
            r = t, g = p, b = v;
            break;
        case 5:
            r = v, g = p, b = q;
            break;
    }
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}
//We are using colors with same value and saturation as highlighters
function wordToColor(word, s = 0.5, v = 1) {
    const n = 5; //so that colors are spread apart
    const h = nPearsonHash(word, n) / Math.pow(2, (8 - n));
    return HSVToRGB(h, s, v);
}
exports.wordToColor = wordToColor;
const extensionpath = vscode.extensions.getExtension("piersdeseilligny.betterfountain").extensionPath;
function resolveAsUri(panel, ...p) {
    const uri = vscode.Uri.file(path.join(extensionpath, ...p));
    return panel.webview.asWebviewUri(uri).toString();
}
exports.resolveAsUri = resolveAsUri;
function getAssetsUri(iconName) {
    return vscode.Uri.file(path.join(extensionpath, "assets", iconName + ".svg"));
}
exports.getAssetsUri = getAssetsUri;
function mapToObject(map) {
    let jsonObject = {};
    map.forEach((value, key) => {
        jsonObject[key] = value;
    });
    return jsonObject;
}
exports.mapToObject = mapToObject;
function componentToHex(c) {
    var hex = c.toString(16);
    return hex.length == 1 ? "0" + hex : hex;
}
function rgbToHex(rgb) {
    return "#" + componentToHex(rgb[0]) + componentToHex(rgb[1]) + componentToHex(rgb[2]);
}
exports.rgbToHex = rgbToHex;
function median(values) {
    if (values.length == 0)
        return 0;
    values.sort(function (a, b) { return a - b; });
    var half = Math.floor(values.length / 2);
    if (values.length % 2)
        return values[half];
    else
        return (values[half - 1] + values[half]) / 2.0;
}
exports.median = median;
//# sourceMappingURL=utils.js.map