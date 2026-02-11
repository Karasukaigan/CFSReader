import locale
import os
import json
from dotenv import get_key, set_key

class I18nManager:
    def __init__(self):
        self.translations = {}
        self.default_lang = 'en'
        self.load_translations()

    def _get_system_language(self):
        def_lang = get_key('.env', 'DEF_LANG')
        if def_lang:
            return def_lang
        try:
            lang, _ = locale.getdefaultlocale()
            if lang:
                primary = lang.split('_')[0]
                set_key('.env', 'DEF_LANG', primary)
                return primary
        except:
            pass
        for var in ['LANG', 'LC_ALL']:
            env_lang = os.environ.get(var)
            if env_lang:
                primary = env_lang.split('.')[0].split('_')[0]
                set_key('.env', 'DEF_LANG', primary)
                return primary
        set_key('.env', 'DEF_LANG', self.default_lang)
        return self.default_lang

    def load_translations(self):
        """Load translation files"""
        try:
            sys_lang = self._get_system_language()
            self.default_lang = sys_lang
            if sys_lang == "en":
                return
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "i18n", f"{sys_lang}.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"Failed to load translations: {e}")

    def tr(self, text):
        """Translate text"""
        return self.translations.get(text, text)

if __name__ == "__main__":
    i18n_manager = I18nManager()
    print(i18n_manager.tr("CFSReader"))