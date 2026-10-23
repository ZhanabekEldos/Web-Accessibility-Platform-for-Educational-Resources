"""Справочные данные WAI-ARIA 1.2, нужные правилам."""

VALID_ROLES = frozenset(
    """
    alert alertdialog application article banner blockquote button caption cell checkbox code columnheader
    combobox complementary contentinfo definition deletion dialog directory document emphasis feed figure form
    generic grid gridcell group heading img insertion link list listbox listitem log main marquee math menu
    menubar menuitem menuitemcheckbox menuitemradio meter navigation none note option paragraph presentation
    progressbar radio radiogroup region row rowgroup rowheader scrollbar search searchbox separator slider
    spinbutton status strong subscript superscript switch tab table tablist tabpanel term textbox time timer
    toolbar tooltip tree treegrid treeitem
    """.split()
)
VALID_ROLE_PREFIXES = ("doc-", "graphics-")

VALID_ARIA_ATTRS = frozenset(
    """
    aria-activedescendant aria-atomic aria-autocomplete aria-braillelabel aria-brailleroledescription aria-busy
    aria-checked aria-colcount aria-colindex aria-colindextext aria-colspan aria-controls aria-current
    aria-describedby aria-description aria-details aria-disabled aria-dropeffect aria-errormessage aria-expanded
    aria-flowto aria-grabbed aria-haspopup aria-hidden aria-invalid aria-keyshortcuts aria-label aria-labelledby
    aria-level aria-live aria-modal aria-multiline aria-multiselectable aria-orientation aria-owns
    aria-placeholder aria-posinset aria-pressed aria-readonly aria-relevant aria-required aria-roledescription
    aria-rowcount aria-rowindex aria-rowindextext aria-rowspan aria-selected aria-setsize aria-sort
    aria-valuemax aria-valuemin aria-valuenow aria-valuetext
    """.split()
)

# Роли, у которых обязательны определённые атрибуты (если состояние не берётся из нативного элемента).
REQUIRED_ATTRS = {
    "checkbox": ("aria-checked",),
    "switch": ("aria-checked",),
    "radio": ("aria-checked",),
    "menuitemcheckbox": ("aria-checked",),
    "menuitemradio": ("aria-checked",),
    "slider": ("aria-valuenow",),
    "scrollbar": ("aria-valuenow", "aria-controls"),
    "meter": ("aria-valuenow",),
    "heading": ("aria-level",),
}

# Атрибуты, значения которых — id других элементов.
IDREF_ATTRS = ("aria-labelledby", "aria-describedby", "aria-controls", "aria-owns", "aria-activedescendant", "aria-flowto", "aria-errormessage", "aria-details")


def is_valid_role(token: str) -> bool:
    return token in VALID_ROLES or token.startswith(VALID_ROLE_PREFIXES)
