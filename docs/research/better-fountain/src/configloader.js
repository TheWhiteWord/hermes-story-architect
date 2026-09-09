"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getFountainConfig = exports.changeFountainUIPersistence = exports.initFountainUIPersistence = exports.uiPersistence = exports.ExportConfig = exports.FountainConfig = void 0;
const vscode = require("vscode");
class FountainConfig {
}
exports.FountainConfig = FountainConfig;
class ExportConfig {
}
exports.ExportConfig = ExportConfig;
exports.uiPersistence = {
    outline_visibleSynopses: true,
    outline_visibleNotes: true,
    outline_visibleScenes: true,
    outline_visibleSections: true
};
let extensionContext = undefined;
var initFountainUIPersistence = function (context) {
    extensionContext = context;
    context.globalState.keys().forEach((k) => {
        var v = context.globalState.get(k);
        if (v != undefined) {
            exports.uiPersistence[k] = v;
        }
    });
    for (const k in exports.uiPersistence) {
        vscode.commands.executeCommand('setContext', 'fountain.uipersistence.' + k, exports.uiPersistence[k]);
    }
};
exports.initFountainUIPersistence = initFountainUIPersistence;
var changeFountainUIPersistence = function (key, value) {
    if (extensionContext) {
        extensionContext.globalState.update(key, value);
        exports.uiPersistence[key] = value;
        vscode.commands.executeCommand('setContext', 'fountain.uipersistence.' + key, value);
    }
};
exports.changeFountainUIPersistence = changeFountainUIPersistence;
var getFountainConfig = function (docuri) {
    if (!docuri && vscode.window.activeTextEditor != undefined)
        docuri = vscode.window.activeTextEditor.document.uri;
    var pdfConfig = vscode.workspace.getConfiguration("fountain.pdf", docuri);
    var generalConfig = vscode.workspace.getConfiguration("fountain.general", docuri);
    return {
        number_scenes_on_save: generalConfig.numberScenesOnSave,
        refresh_stats_on_save: generalConfig.refreshStatisticsOnSave,
        refresh_pdfpreview_on_save: generalConfig.refreshPdfPreviewOnSave,
        embolden_scene_headers: pdfConfig.emboldenSceneHeaders,
        embolden_character_names: pdfConfig.emboldenCharacterNames,
        show_page_numbers: pdfConfig.showPageNumbers,
        split_dialogue: pdfConfig.splitDialog,
        print_title_page: pdfConfig.printTitlePage,
        print_profile: pdfConfig.printProfile,
        double_space_between_scenes: pdfConfig.doubleSpaceBetweenScenes,
        print_sections: pdfConfig.printSections,
        print_synopsis: pdfConfig.printSynopsis,
        print_actions: pdfConfig.printActions,
        print_headers: pdfConfig.printHeaders,
        print_dialogues: pdfConfig.printDialogues,
        number_sections: pdfConfig.numberSections,
        use_dual_dialogue: pdfConfig.useDualDialogue,
        print_notes: pdfConfig.printNotes,
        print_header: pdfConfig.pageHeader,
        print_footer: pdfConfig.pageFooter,
        print_watermark: pdfConfig.watermark,
        scenes_numbers: pdfConfig.sceneNumbers,
        each_scene_on_new_page: pdfConfig.eachSceneOnNewPage,
        merge_empty_lines: pdfConfig.mergeEmptyLines,
        print_dialogue_numbers: pdfConfig.showDialogueNumbers,
        create_bookmarks: pdfConfig.createBookmarks,
        invisible_section_bookmarks: pdfConfig.invisibleSectionBookmarks,
        text_more: pdfConfig.textMORE,
        text_contd: pdfConfig.textCONTD,
        text_scene_continued: pdfConfig.textSceneContinued,
        scene_continuation_top: pdfConfig.sceneContinuationTop,
        scene_continuation_bottom: pdfConfig.sceneContinuationBottom,
        synchronized_markup_and_preview: generalConfig.synchronizedMarkupAndPreview,
        preview_theme: generalConfig.previewTheme,
        preview_texture: generalConfig.previewTexture,
        parenthetical_newline_helper: generalConfig.parentheticalNewLineHelper
    };
};
exports.getFountainConfig = getFountainConfig;
//# sourceMappingURL=configloader.js.map