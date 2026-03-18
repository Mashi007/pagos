path = "src/components/clientes/ExcelUploaderUI.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """                                    ) : esDuplicado ? (
                                      <div className="flex flex-col items-center text-red-700 text-xs">
                                        <span>No se puede guardar</span>
                                        <span className="text-[10px] font-medium" title={motivosDuplicado.join('; ')}>
                                          {columnasDuplicadas(motivosDuplicado)}
                                        </span>
                                      </div>
                                    ) : isClientValid(row) ? ("""

new = """                                    ) : esDuplicado ? (
                                      <div className="flex flex-col items-center text-red-700 text-xs">
                                        {esCedulaNoAcepta ? (
                                          <span className="font-semibold">No se acepta</span>
                                        ) : (
                                          <>
                                            <span>No se puede guardar</span>
                                            <span className="text-[10px] font-medium" title={motivosDuplicado.join('; ')}>
                                              {columnasDuplicadas(motivosDuplicado)}
                                            </span>
                                          </>
                                        )}
                                      </div>
                                    ) : isClientValid(row) ? ("""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced OK")
else:
    print("Block not found")
    # try without leading spaces
    old2 = old.replace("                                    ", "  ")
    if old2 in content:
        content = content.replace(old2, new.replace("                                    ", "  "))
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Replaced (alt spacing) OK")
