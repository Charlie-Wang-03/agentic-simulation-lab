# SpaceClaim/Discovery script, API version selected by /ScriptAPI=261.
# ``args[0]`` is the output .scdocx path.

ClearAll()

BlockBody.Create(
    Point.Create(MM(0), MM(-10), MM(-5)),
    Point.Create(MM(200), MM(10), MM(5)),
)

BlockBody.Create(
    Point.Create(MM(200), MM(-10), MM(-5)),
    Point.Create(MM(400), MM(10), MM(5)),
    ExtrudeType.ForceIndependent,
    None,
)

DocumentSave.Execute(str(args[0]))
