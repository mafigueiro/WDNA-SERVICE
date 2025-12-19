# Manifiesto

## Nuestro proyecto
Una plantilla de repositorio para proyectos Python orientados a datos, lista para ser copiada y adaptada, con buenas prácticas de desarrollo de software y automatizaciones CI/CD out-of-the-box.
Más que un recurso conveniente con el que agilizar los desarrollos: una referencia de decisiones técnicas y herramientas seleccionadas que representan y moldean la cultura de trabajo del equipo.

## Nuestro público
Mientras que el público principal somos los propios desarrolladores de la línea AI&DataOPS, fomentamos el uso (y colaboración) por parte de cualquier persona o equipo interesado.
Queremos que sea útil desde el primer momento, tanto para quienes están dando sus primeros pasos y necesitan un punto de partida, como para quienes saben lo que quieren y buscan una base sólida.

## Nuestros principios
### I. Buenas prácticas y estándares
Desarrollamos aplicaciones en contenedores, sin estado, y con la lógica separada de los datos y la configuración ([12-factor apps](https://12factor.net/)).
Preferimos un flujo de trabajo automatizado, basado en CI/CD y operaciones Git. Promovemos la seguridad y el *testing* extensivo, a ser posible a través de TDD. No nos limitamos a *tooling* y *boilerplate*, también abogamos por arquitectura hexagonal, principios SOLID, e intentamos adaptar conceptos de DDD al mundo intensivo en datos en el que nos movemos.
Aplicamos [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) y [Semantic Versioning](https://semver.org/), e intentamos adherirnos a las PEPs, mantener un *pyproject.toml* estándar, y seguir unas reglas de estilo.

### II. Facilitación y simplificación
El objetivo final de esta plantilla es simplificar la vida del desarrollador, permitiéndole desarrollar código de mayor calidad con el menor coste cognitivo posible. Por eso la plantilla debe ser, ante todo, fácil de adoptar.
Idealmente, ahorrará mucho tiempo en el *setup* inicial de los proyectos y tomará mucha decisiones por el desarrollador, que quedará libre para dedicar su atención a resolver problemas de negocio.

### III. Mantenimiento y adaptación
La plantilla debe evolucionar a medida que lo hacen las necesidades de la línea, adaptándose a nuevas ideas y aprendizajes; cualquier decisión que se convierta en un obstáculo será susceptible de ser cambiada. Siendo un esfuerzo colaborativo, siempre estará abierta a discusión y aportaciones.
Por otro lado, un buen sistema de control de versiones, resumen de cambios y comunicación de mejoras mantendrá a los consumidores de la plantilla al día. 

### IV. Consistencia
El carácter estándar de la plantilla no solo será un apoyo en el desarrollo, sino que marcará la forma de usar, documentar, distribuir y desplegar el producto de software resultante. La adopción a lo largo de Gradiant nos dará consistencia y robustez a ojos de cliente y facilitará la colaboración entre equipos.
