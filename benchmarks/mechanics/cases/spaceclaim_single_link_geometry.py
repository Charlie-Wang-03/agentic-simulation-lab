"""SpaceClaim 261 headless script: create one independent rectangular link."""

ClearAll()
BlockBody.Create(Point.Create(MM(0), MM(-10), MM(-5)), Point.Create(MM(200), MM(10), MM(5)))
DocumentSave.Execute(str(args[0]))
