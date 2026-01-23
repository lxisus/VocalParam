# Flujo de Trabajo Profesional

Este proyecto sigue estándares de la industria para asegurar la calidad y automatización.

## Automatización con CI/CD

VocalParam usa **GitHub Actions** para:
- **Validación**: Cada cambio enviado a GitHub activa los tests unitarios.
- **Documentación en Vivo**: Si los tests pasan, el manual se actualiza automáticamente en la web del proyecto.

## Reglas de Commits

Usamos **Conventional Commits**:
- `feat`: Nuevas características.
- `fix`: Correcciones.
- `docs`: Documentación.
- `refactor`: Mejoras de código.

## Desarrollo Basado en Tests (TDD)

Cada componente core tiene su suite de pruebas correspondiente en el directorio `tests/`. Esto permite que el proyecto sea robusto ante cambios repentinos de arquitectura.
