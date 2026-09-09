// Standalone Better Fountain parser — extracted from the VS Code extension
const path = require('path');
const Module = require('module');

const vscodeStub = {
    Position: class { 
        constructor(line, character) { this.line = line; this.character = character; } 
    },
    Range: class { 
        constructor(start, end) { this.start = start; this.end = end; } 
    },
    Selection: class extends (class {}) {},
    TreeItem: class { constructor(label) { this.label = label; } },
    window: { 
        activeTextEditor: undefined, 
        visibleTextEditors: [], 
        createTextEditorDecorationType: () => ({}),
        onDidChangeTextEditorSelection: () => {},
        onDidChangeActiveTextEditor: () => {},
        showInformationMessage: () => {},
        showErrorMessage: () => {}
    },
    workspace: {
        onDidChangeConfiguration: () => {},
        onDidChangeTextDocument: () => {},
        getConfiguration: () => ({
            get: (key, defaultValue) => defaultValue
        })
    },
    Uri: { 
        parse: () => ({}), 
        file: () => ({}) 
    },
    extensions: {
        getExtension: () => ({
            packageJSON: { name: 'better-fountain', version: '1.14.2', aiKey: '' }
        })
    },
    commands: {
        registerCommand: () => {},
        executeCommand: () => {}
    }
};

const origResolve = Module._resolveFilename;
Module._resolveFilename = function(req, ...args) {
    if (req === 'vscode') return path.resolve('/tmp/vscode-stub/index.js');
    return origResolve.call(this, req, ...args);
};

const stubs = {
    './utils': {
        parseLocationInformation: (scene_heading) => {
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
        },
        trimCharacterExtension: (character) => character.replace(/[ \t]*(\\(.*\\))[ \t]*([ \t]*\^)?$/, ""),
        trimCharacterForceSymbol: (character) => character.replace(/^[ \t]*@/, ""),
        calculateDialogueDuration: (dialogue) => {
            var duration = 0;
            var sanitized = dialogue.replace(/[^\w]/gi, '');
            duration += ((sanitized.length) / 3) * 0.1945548;
            var punctuationMatches = dialogue.match(/(\.|\?|\!|\:) |(\, )/g);
            if (punctuationMatches) {
                if (punctuationMatches[0]) duration += 0.75 * punctuationMatches[0].length;
                if (punctuationMatches[1]) duration += 0.3 * punctuationMatches[1].length;
            }
            return duration;
        },
        slugify: (text) => text.toString().toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^\w-]+/g, '')
            .replace(/-{2,}/g, '-')
            .replace(/^-+/, '')
            .replace(/-+$/, ''),
        last: (array) => array[array.length - 1]
    },
    './token': {
        create_token: (text, cursor, line, new_line_length, type) => {
            var t = {
                text: text, type: type, start: cursor, end: cursor, line: line,
                ignore: false, number: undefined, dual: undefined, html: undefined,
                level: undefined, time: undefined, character: undefined,
                index: -1, takeNumber: -1, original_line: undefined,
                is: function(...args) { return args.indexOf(this.type) !== -1; },
                is_dialogue: function() { return this.is("character", "parenthetical", "dialogue"); },
                name: function() {
                    var character = this.text;
                    var p = character.indexOf("(");
                    if (p !== -1) character = character.substring(0, p);
                    return character.trim();
                },
                location: function() {
                    var location = this.text.trim();
                    location = location.replace(/^(INT\.?\/EXT\.?)|(I\/E)|(INT\.?)|(EXT\.?)/, "");
                    var dash = location.lastIndexOf(" - ");
                    if (dash !== -1) location = location.substring(0, dash);
                    return location.trim();
                },
                has_scene_time: function(time) {
                    var suffix = this.text.substring(this.text.indexOf(" - "));
                    return this.is("scene_heading") && suffix.indexOf(time) !== -1;
                },
                location_type: function() {
                    var location = this.text.trim();
                    if (/^I(NT.?)?\/E(XT.?)?/.test(location)) return "mixed";
                    else if (/^INT.?/.test(location)) return "int";
                    else if (/^EXT.?/.test(location)) return "ext";
                    return "other";
                }
            };
            if (text) t.end = cursor + text.length - 1 + new_line_length;
            return t;
        }
    },
    './configloader': {
        getFountainConfig: () => ({
            print_notes: true,
            print_dialogue_numbers: false,
            use_dual_dialogue: true,
            merge_multiple_empty_lines: false,
            each_scene_on_new_page: false,
            embolden_scene_headers: false
        })
    },
    './providers/Decorations': {
        AddDialogueNumberDecoration: () => {}
    },
    './helpers': {
        default: {
            sort_index: (a, b) => {
                if (a.index == -1) return 0;
                return a.index - b.index;
            }
        }
    }
};

const origLoad = Module._load;
Module._load = function(req, ...args) {
    if (req === 'vscode') return vscodeStub;
    if (stubs[req]) return stubs[req];
    return origLoad.call(this, req, ...args);
};

const parser = require('/home/davide/.vscode/extensions/piersdeseilligny.betterfountain-1.14.2/out/afterwriting-parser.js');
const fs = require('fs');
const text = fs.readFileSync(process.argv[2], 'utf-8');
const result = parser.parse(text, {}, false);

// Convert Maps to plain objects for JSON serialization
function mapToObject(map) {
    const obj = {};
    map.forEach((value, key) => { obj[key] = value; });
    return obj;
}

result.properties.characters = mapToObject(result.properties.characters);
result.properties.locations = mapToObject(result.properties.locations);

const obj = JSON.parse(JSON.stringify(result));
fs.writeFileSync(process.argv[3], JSON.stringify(obj, null, 2));
console.log('Tokens:', result.tokens.length);
console.log('Scenes:', result.properties.scenes.length);
console.log('Characters:', Object.keys(result.properties.characters).length);
console.log('Locations:', Object.keys(result.properties.locations).length);
