# Output data format

The spider writes two JSON files (UTF-8, accents kept as-is) to `OUTPUT_DIR`
(default `<repo>/data/`).

## `output.json`

A list of departments:

```jsonc
[
  {
    "title": "Bioquímica y Biología Estructural",
    "url": "https://www.ifc.unam.mx/bioquimica.php",
    "relative_url": "bioquimica.php",
    "Researchers": {
      "Roberto Coria Ortega": {
        "Researcher link": "https://www.ifc.unam.mx/investigador-perfil.php?id=5",
        "researcher info": [
          "Intereses de Investigación",
          "Estudio de los mecanismos de homeostasis mitocondrial en levaduras…",
          "Trayectoria Profesional",
          "Investigador Titular C",
          "Formación Académica",
          "Licenciado en Biología, Facultad de Ciencias, UNAM, México (1983)",
          "Líneas de Investigación",
          "…"
        ],
        "email": "…@ifc.unam.mx"
      }
    }
  }
]
```



## Fields

### Department

| Field | Type | Description |
|---|---|---|
| `title` | string | Department name |
| `url` | string | Absolute URL of the department page |
| `relative_url` | string | Link as it appears on the index page |
| `Researchers` | object | Researcher name → researcher record |

### Researcher record

| Field | Type | Description |
|---|---|---|
| `Researcher link` | string | Absolute URL of the profile page |
| `researcher info` | list of strings | Text nodes from the profile, in page order (see below) |
| `email` | string or null | Contact e-mail, or `null` if none was found |
| `extraction_failed` | bool (optional) | `true` if the profile loaded but no text was found |
| `request_failed` | bool (optional) | `true` if the profile request failed |
| `error` | string (optional) | Error message when `request_failed` is set |

### `researcher info` structure

The list is flat. Section headings appear as items, each followed by that
section's content. Typical headings:

* `Intereses de Investigación`: free-text research interests (the richest
  field for NLP)
* `Trayectoria Profesional`: academic rank
* `Posdoctorados y Estancias`: postdocs and research stays
* `Formación Académica`: degrees
* `Líneas de Investigación`: research lines (short topic labels)

Not every profile has every section, and the order can vary. To split the list
into sections, treat each known heading as a key and collect the items after
it until the next heading.

## Snapshot statistics (last run)

| Department | Researchers |
|---|---|
| Bioquímica y Biología Estructural | 9 |
| Genética Molecular | 11 |
| Biología Celular y Desarrollo | 11 |
| Neurociencia Cognitiva | 12 |
| Neurodesarrollo y Fisiología | 8 |
| Neuropatología Molecular | 8 |
| **Total** | **59** (all with profile text and e-mail) |

## Privacy

These files contain names and e-mail addresses, so `.gitignore` excludes
them. Do not commit them to a public repository.
