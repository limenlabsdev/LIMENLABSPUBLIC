import rhino3dm as r

from diff3dm.inventory import duplicates, layers, tags
from diff3dm.snapshot import read_model


def test_saved_model_reports(tmp_path):
    model = r.File3dm()
    model.Strings["issue"] = "P01"
    for name in ("Walls", "Grid", "Empty"):
        layer = r.Layer()
        layer.Name = name
        model.Layers.Add(layer)
    ids = []
    for index in (0, 1):
        attrs = r.ObjectAttributes()
        attrs.LayerIndex = index
        attrs.Name = "A" if index == 0 else "B"
        if index == 1:
            attrs.SetUserString("mark", "LB")
        ids.append(str(model.Objects.AddPoint(r.Point3d(1, 2, 3), attrs)))
    model.Objects.AddPoint(r.Point3d(2, 2, 3))
    path = tmp_path / "handoff.3dm"
    assert model.Write(str(path), 8)
    saved = read_model(str(path))
    counts = {row["path"]: row["objects"] for row in layers(saved)}
    assert counts["Grid"] == 1 and counts["Empty"] == 0 and sum(counts.values()) == 3
    assert tags(saved) == {"document": {"issue": "P01"},
                           "objects": [{"id": ids[1], "name": "B", "values": {"mark": "LB"}}]}
    result = duplicates(saved)
    assert result["unhashed_object_ids"] == []
    assert [g["object_ids"] for g in result["groups"]] == [sorted(ids)]

def test_unresolved_layer_index_is_counted():
    from types import SimpleNamespace

    orphan = SimpleNamespace(Attributes=SimpleNamespace(LayerIndex=-1))
    assert layers(SimpleNamespace(Objects=[orphan], Layers=[])) == [
        {"id": None, "index": -1, "path": None, "objects": 1, "visible": None, "locked": None}
    ]


def test_named_views_only_in_archive_order(tmp_path):
    from diff3dm.inventory import named_views

    model = r.File3dm()
    plan = r.ViewInfo()
    plan.Name = "Roof plan"
    plan.Viewport = r.ViewportInfo.DefaultTop()
    model.Views.Add(plan)
    assert named_views(model) == []
    model.NamedViews.Add(plan)
    view = r.ViewInfo()
    view.Name = "Entrance"
    view.Viewport = r.ViewportInfo.DefaultPerspective()
    assert view.Viewport.ChangeToPerspectiveProjection(10, True, 50)
    model.NamedViews.Add(view)
    path = tmp_path / "cameras.3dm"
    assert model.Write(str(path), 8)
    rows = named_views(read_model(str(path)))
    assert [(row["name"], row["projection"]) for row in rows] == [
        ("Roof plan", "parallel"), ("Entrance", "perspective")]
    assert rows[0]["camera_location"] == [0, 0, 100]
    assert rows[0]["camera_up"] == [0, 1, 0]
    assert rows[0]["camera_direction"] == [0, 0, -1]
