# Cómo cortar una release

Este repo mantiene **dos** changelogs, para dos audiencias:

| Documento | Herramienta | Audiencia | Cuándo se genera |
|---|---|---|---|
| `CHANGELOG.md` | git-cliff | desarrolladores | al cortar la release (este runbook) |
| `docs/releases/CHANGELOG-USUARIO.md` | towncrier + edición humana | geólogos / clientes | al cortar la release |

No hay workflow que reescriba changelogs en cada push a `main`: se generan acá,
en un solo commit, sin loops de bot y sin pelear con branch protection.

## Pasos

```bash
git checkout main && git pull
VERSION=1.1.0          # sin la "v"

# 1. Notas de usuario: junta los fragments y borra changelog.d/*
uv run towncrier build --yes --version "$VERSION"

# 2. Pulí a mano docs/releases/CHANGELOG-USUARIO.md (~20 min):
#    highlights, capturas, GIFs (guardados en docs/releases/assets/$VERSION/).

# 3. Changelog técnico desde el historial git
uv run git-cliff --tag "v$VERSION" --output CHANGELOG.md
#    (o el binario git-cliff si lo tenés instalado global)

# 4. Subí la versión en pyproject.toml al valor de $VERSION.

# 5. Un commit, un tag, push
git commit -am "chore: release v$VERSION"
git tag "v$VERSION"
git push && git push origin "v$VERSION"
```

Al pushear el tag, `.github/workflows/release.yml` publica el GitHub Release
(usando `.github/release.yml` para agrupar por labels). Editá el Release para
pegar los highlights de usuario si querés que aparezcan también ahí.

## Labels (setup único en GitHub UI)

Creá estos labels para que funcionen los chequeos y el agrupado:

- `sin-changelog` - salta el chequeo obligatorio de fragment.
- `feat`, `fix`, `docs` - agrupan PRs en secciones del GitHub Release (`.github/release.yml`).
