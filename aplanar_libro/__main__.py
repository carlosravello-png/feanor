from .cli import main

# La guarda es necesaria en Windows: cada proceso de trabajo vuelve a importar
# este módulo, y sin ella cada uno arrancaría el programa entero otra vez.
if __name__ == "__main__":
    main()
