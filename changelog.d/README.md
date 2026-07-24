# changelog.d - fragments de notas para el usuario

Cada PR que cambie algo visible para el usuario agrega **un** archivo acá. Al
liberar una versión, `towncrier build` los junta en
[`docs/releases/CHANGELOG-USUARIO.md`](../docs/releases/CHANGELOG-USUARIO.md) y
los borra. Como cada PR escribe su propio archivo, no hay conflictos de merge.

## Nombre del archivo

```
<numero-de-PR>.<tipo>.md
```

Ejemplos:

```
122.nuevo.md    → "La visualización 3D ahora acepta validación cruzada por bloques."
124.arreglo.md  → "El kriging ordinario ya no falla con dominios de menos de 5 muestras."
```

## Tipos

| Tipo      | Sección en las notas       | ¿Muestra el texto? |
|-----------|----------------------------|--------------------|
| `rompe`   | Cambios incompatibles      | sí                 |
| `nuevo`   | Novedades                  | sí                 |
| `arreglo` | Correcciones               | sí                 |
| `interno` | Interno                    | no (solo cuenta)   |

## Cómo escribir el texto

Una o dos frases que un geólogo entienda. Sin números de PR, sin nombres de
funciones. Markdown se pasa tal cual, así que podés incrustar imágenes:

```markdown
La visualización 3D ahora acepta validación cruzada por bloques.

![validación cruzada](../docs/releases/assets/1.1.0/cross-validation.png)
```

Guardá los assets en `docs/releases/assets/<version>/`.

## ¿Y si no aplica al usuario?

Usá `interno` (no aparece en las notas), o etiquetá el PR con `sin-changelog`
para saltar el chequeo obligatorio.
