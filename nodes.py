from ryven.NENV import *

widgets = import_widgets(__file__)

from pyvis.network import Network
import json
import os
from rdflib import Graph
import pandas as pd
from influxdb import InfluxDBClient
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from SPARQLWrapper import SPARQLWrapper, JSON
from enum import Enum


class ShowLiteral(Enum):
    Yes = 0
    No = 1
    InNode = 2


class Ontology:
    def __init__(self, ontology):
        self.ontology = ontology


class Visualization(object):
    def __init__(
        self, endpoint=None, filepath=None, ignore_property=[], notebook=False,
    ):

        self.__filepath = filepath
        self.__ignore_property = ignore_property if ignore_property != None else []
        self.__sparql = SPARQLWrapper(endpoint)
        self.__useArrow = True
        self.__notebook = notebook

    def __getLocalName(self, node):
        if node.find("/") > 0 and node.find("#") > 0:
            return (
                node[node.rindex("/") + 1 :]
                if node.rindex("/") > node.rindex("#")
                else node[node.rindex("#") + 1 :]
            )
        elif node.find("/") > 0:
            return node[node.rindex("/") + 1 :]
        elif node.find("#") > 0:
            return node[node.rindex("#") + 1 :]
        else:
            return node

    def useArrow(self, flag=True):
        self.__useArrow = flag

    def __make_short_name(self, name):
        if len(name) > 20:
            name = name[0:20]
        return name

    def setIgnoreProperty(self, ignore_property):
        self.__ignore_property = ignore_property

    def __show_graph(self, results, show_literal):
        width = "100%" if self.__notebook else "70%"
        nw = Network(height="800px", width=width, notebook=self.__notebook)

        node = {}
        groups = {}
        node_num = 0
        group_num = 0
        edge_list = []

        if show_literal:
            groups["literal"] = group_num
            group_num += 1

        for result in results["results"]["bindings"]:
            if not result["p"]["value"] in self.__ignore_property:
                if "slabel" not in result:
                    result["slabel"] = {
                        "type": "literal",
                        "value": self.__getLocalName(result["s"]["value"]),
                    }
                if "olabel" not in result:
                    result["olabel"] = {
                        "type": "literal",
                        "value": self.__getLocalName(result["o"]["value"]),
                    }
                if "stype" not in result:
                    result["stype"] = {"type": "literal", "value": ""}
                if "otype" not in result:
                    result["otype"] = {"type": "literal", "value": ""}

                # Node
                if result["s"]["type"] == "uri" and not result["s"]["value"] in node:
                    node[result["s"]["value"]] = {"id": node_num}
                    node_num += 1

                if result["o"]["type"] == "uri" and not result["o"]["value"] in node:
                    node[result["o"]["value"]] = {"id": node_num}
                    node_num += 1

                if "stype" in result and not result["stype"]["value"] in groups:
                    groups[result["stype"]["value"]] = group_num
                    group_num += 1
                if "otype" in result and not result["otype"]["value"] in groups:
                    groups[result["otype"]["value"]] = group_num
                    group_num += 1

                node[result["s"]["value"]].update(
                    {
                        "label": result["slabel"]["value"],
                        "type": result["stype"]["value"],
                    }
                )
                if result["o"]["type"] == "uri":
                    node[result["o"]["value"]].update(
                        {
                            "label": result["olabel"]["value"],
                            "type": result["otype"]["value"],
                        }
                    )
                    edge_list.append(
                        (
                            result["s"]["value"],
                            result["o"]["value"],
                            result["p"]["value"],
                        )
                    )

                # show literal
                if show_literal == ShowLiteral.Yes:
                    if result["o"]["type"] == "literal":
                        node[result["o"]["value"] + str(node_num)] = {"id": node_num}
                        node[result["o"]["value"] + str(node_num)].update(
                            {"label": result["o"]["value"], "type": "literal"}
                        )
                        edge_list.append(
                            (
                                result["s"]["value"],
                                result["o"]["value"],
                                result["p"]["value"],
                                result["o"]["value"] + str(node_num),
                            )
                        )
                        node_num += 1

                # show literal in node tooltip
                if show_literal == ShowLiteral.InNode:
                    if result["o"]["type"] == "literal":
                        if "datatype" in node[result["s"]["value"]]:
                            dt = (
                                node[result["s"]["value"]]["datatype"]
                                + "<br>"
                                + self.__getLocalName(result["p"]["value"])
                                + ":"
                                + result["o"]["value"]
                            )
                            node[result["s"]["value"]].update({"datatype": dt})
                        else:
                            node[result["s"]["value"]]["datatype"] = (
                                self.__getLocalName(result["p"]["value"])
                                + ":"
                                + result["o"]["value"]
                            )
                            node[result["s"]["value"]].update(
                                {"datatype": node[result["s"]["value"]]["datatype"]}
                            )

        for n in node:
            if node[n]["type"] == "literal":
                nw.add_node(
                    n,
                    shape="box",
                    label=self.__make_short_name(node[n]["label"]),
                    title=node[n]["label"],
                    group=groups[node[n]["type"]],
                )
            else:
                if "datatype" in node[n]:
                    nw.add_node(
                        n,
                        label=self.__make_short_name(node[n]["label"]),
                        title=n + "<br>" + node[n]["datatype"],
                        group=groups[node[n]["type"]],
                    )
                else:
                    nw.add_node(
                        n,
                        label=self.__make_short_name(node[n]["label"]),
                        title=n,
                        group=groups[node[n]["type"]],
                    )
        for e in edge_list:
            if len(e) == 4:
                if self.__useArrow:
                    nw.add_edge(
                        e[0],
                        e[3],
                        arrows="to",
                        label=self.__getLocalName(e[2]),
                        title=e[2],
                    )
                else:
                    nw.add_edge(e[0], e[3], label=self.__getLocalName(e[2]), title=e[2])
            else:
                if e[2] == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                    if self.__useArrow:
                        nw.add_edge(
                            e[0],
                            e[1],
                            width=4,
                            color="black",
                            arrows="to",
                            label=self.__getLocalName(e[2]),
                            title=e[2],
                        )
                    else:
                        nw.add_edge(
                            e[0],
                            e[1],
                            width=4,
                            color="black",
                            label=self.__getLocalName(e[2]),
                            title=e[2],
                        )
                else:
                    if self.__useArrow:
                        nw.add_edge(
                            e[0],
                            e[1],
                            arrows="to",
                            label=self.__getLocalName(e[2]),
                            title=e[2],
                        )
                    else:
                        nw.add_edge(
                            e[0], e[1], label=self.__getLocalName(e[2]), title=e[2]
                        )

        nw.set_edge_smooth("dynamic")
        nw.show_buttons(filter_=["physics"])

        return nw

    def vis(
        self,
        query_string_inp: str = "",
        limit: int = 500,
        show_literal: ShowLiteral = ShowLiteral.No,
    ):
        if limit > 1500:
            limit = 1500
        if query_string_inp == "":
            query_string = (
                """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT *
WHERE {
    ?s ?p ?o.
    optional{?s rdfs:label ?slabel .}
    optional{?s a ?stype}
    optional{?o rdfs:label ?olabel .}
    optional{?o a ?otype}
} LIMIT %i
"""
                % limit
            )
        else:
            query_string = query_string_inp

        return self.__run_query(query_string, show_literal)

    def __run_query(self, query_string, show_literal):
        self.__sparql.setQuery(query_string)
        self.__sparql.setReturnFormat(JSON)
        results = self.__sparql.query().convert()
        try:
            nw = self.__show_graph(results, show_literal)
        except Exception as e:
            print(e)
            nw = None
        df = pd.DataFrame().from_dict(results["results"]["bindings"], orient="columns")
        return nw, df

    def vis_file(
        self,
        query_string_inp: str = "",
        show_literal: ShowLiteral = ShowLiteral.Yes,
        limit: int = 500,
    ):
        g = Graph()
        g.parse(self.__filepath, format="turtle")
        if limit > 1500:
            limit = 1500

        if query_string_inp == "":
            query_string = (
                """
                prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT *
                WHERE {
                    ?s ?p ?o.
                    optional{?s rdfs:label ?slabel .}
                    optional{?s a ?stype}
                    optional{?o rdfs:label ?olabel .}
                    optional{?o a ?otype}
                }  LIMIT %i
            """
                % limit
            )
        else:
            query_string = query_string_inp

        qres = g.query(query_string)

        f = open("json_result", "w")
        JSONResultSerializer(qres).serialize(f)
        with open("json_result") as f:
            read_data = json.load(f)
        try:
            nw = self.__show_graph(read_data, show_literal)
        except Exception as e:
            print(e)
            nw = None
        df = pd.DataFrame().from_dict(
            read_data["results"]["bindings"], orient="columns"
        )
        return nw, df


class NodeBase(Node):
    color = "#00a6ff"


class Watch(NodeBase):
    """Simply shows the results"""

    version = "v1.0"
    title = "Watch"
    init_inputs = [
        NodeInputBP(type_="data"),
    ]
    main_widget_class = widgets.WatchWidget
    main_widget_pos = "between ports"

    def __init__(self, params):
        super().__init__(params)
        self.val = None

    def place_event(self):
        self.update()

    def view_place_event(self):
        self.main_widget().show_val(self.val)

    def update_event(self, input_called=-1):
        self.val = self.input(0)
        if self.session.gui:
            self.main_widget().show_val(self.val)


class ReadOntology(NodeBase):
    """Reads the ontology"""

    title = "Read Ontology"
    input_widget_classes = {"choose file IW": widgets.ChooseFileInputWidget}
    init_inputs = [
        NodeInputBP(
            "filepath",
            add_data={"widget name": "choose file IW", "widget pos": "besides"},
        ),
        NodeInputBP(
            " endpoint",
            dtype=dtypes.String(default="http://127.0.0.1:3030/mulberrypond/query"),
        ),
        NodeInputBP(
            " query", dtype=dtypes.String(default="SELECT * WHERE {?s ?p ?o.}")
        ),
        NodeInputBP(" show graph", dtype=dtypes.Boolean()),
        NodeInputBP("limit", dtype=dtypes.Integer(default=25)),
    ]
    init_outputs = [
        NodeOutputBP("ontology"),
        # NodeOutputBP('test')
    ]

    def __init__(self, params):
        super().__init__(params)

        self.onto_path = None
        self.endpoint = None
        self.query = None
        self.show_graph = False
        self.limit = None

    def view_place_event(self):
        self.input_widget(0).path_chosen.connect(self.path_chosen)

    def get_state(self):
        data = {"ontology file path": self.onto_path}
        return data

    def set_state(self, data):
        self.path_chosen(data["ontology file path"])

    def path_chosen(self, file_path):
        self.onto_path = file_path
        self.update()

    def update_event(self, inp=-1):
        self.endpoint = self.input(1)
        self.query = self.input(2) if self.input(2) is not None else ""
        self.show_graph = self.input(3) if self.input(3) is not None else False
        self.limit = self.input(4)
        # print(self.query, type(self.query))
        if self.onto_path is not None:
            try:
                onto = Visualization(filepath=self.onto_path)
                nw, df = onto.vis_file(query_string_inp=self.query, limit=self.limit)
                if self.show_graph == True:
                    result = "temp.html"
                    nw.show(result)
                self.set_output_val(0, df)
            except Exception as e:
                print(e)
        if self.endpoint is not None and self.onto_path is None:
            try:
                onto = Visualization(self.endpoint)
                nw, df = onto.vis(query_string_inp=self.query, limit=self.limit)
                if self.show_graph == True:
                    result = "temp.html"
                    nw.show(result)
                self.set_output_val(0, df)
            except Exception as e:
                print(e)


def convertList(Ontology):
    prefix = []
    entity = []
    for item in Ontology:
        if "#" in item["value"]:
            temp_list = item["value"].split("#")
            if temp_list[0] not in prefix:
                prefix.append(temp_list[0])
            if temp_list[1] not in entity:
                entity.append(temp_list[1])
    return prefix, entity


class OntoData(NodeBase):
    """Convert Queryed DataFrame to Lists"""

    title = "OntoData"
    init_inputs = [
        NodeInputBP(" ontology"),
    ]
    init_outputs = [
        NodeOutputBP("subject namespace"),
        NodeOutputBP("subject"),
        NodeOutputBP("predicate namespace"),
        NodeOutputBP("predicate"),
        NodeOutputBP("object namespace"),
        NodeOutputBP("object"),
    ]

    def __init__(self, params):
        super().__init__(params)

    def update_event(self, inp=-1):
        ontology = self.input(0)

        subject_prefix, subject = convertList(ontology["s"])
        predicate_prefix, predicate = convertList(ontology["p"])
        object_prefix, object = convertList(ontology["o"])
        self.set_output_val(0, subject_prefix)
        self.set_output_val(1, subject)
        self.set_output_val(2, predicate_prefix)
        self.set_output_val(3, predicate)
        self.set_output_val(4, object_prefix)
        self.set_output_val(5, object)


class Select(NodeBase):
    title = "Select"
    init_inputs = [
        NodeInputBP(),
        NodeInputBP("No.", dtype=dtypes.Integer(default=0)),
    ]
    init_outputs = [
        NodeOutputBP(),
    ]
    main_widget_class = widgets.SmallWatchWidget
    main_widget_pos = "below ports"

    def __init__(self, params):
        super().__init__(params)
        self.__num = None
        self.val = None

    def place_event(self):
        self.update()

    def view_place_event(self):
        self.main_widget().show_val(self.val)

    def update_event(self, inp=-1):
        self.__num = self.input(1)
        position = self.input(0)
        self.val = position[self.__num]
        if self.session.gui:
            self.main_widget().show_val(self.val)
        self.set_output_val(0, self.val)


class IDBuilder(NodeBase):
    """Costume ID for Query"""

    title = "ID Builder"
    init_inputs = [
        NodeInputBP(
            "namespace",
            dtype=dtypes.String(
                default="https://brickschema.org/schema/Brick", size="l"
            ),
        ),
        NodeInputBP("entity", dtype=dtypes.String(default="AHU", size="l")),
    ]
    init_outputs = [
        NodeOutputBP("id"),
    ]

    def update_event(self, inp=-1):
        prefix = self.input(0)
        entity = self.input(1)
        id = f"{prefix}#{entity}"
        self.set_output_val(0, id)


class GQueryBuilder(NodeBase):
    """Build Query for Graph Database"""

    title = "GQ Builder"
    init_inputs = [
        NodeInputBP("subject"),
        NodeInputBP("predicate"),
        NodeInputBP("object"),
    ]
    init_outputs = [
        NodeOutputBP("query"),
    ]

    def __init__(self, params):
        super().__init__(params)

        self.query = None
        self.subject = None
        self.predicate = None
        self.object = None

    def update_event(self, inp=-1):
        self.subject = f"?s=<{self.input(0)}>" if self.input(0) is not None else None
        self.predicate = f"?p=<{self.input(1)}>" if self.input(1) is not None else None
        self.object = f"?o=<{self.input(2)}>" if self.input(2) is not None else None
        filter = []
        for item in (self.subject, self.predicate, self.object):
            if item is not None:
                filter.append(item)
        filter = " && ".join(filter)
        self.query = """
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT *
WHERE {
    filter(%s)
    ?s ?p ?o.
    optional{?s rdfs:label ?slabel .}
    optional{?s a ?stype}
    optional{?o rdfs:label ?olabel .}
    optional{?o a ?otype}
}
""" % (
            filter,
        )
        self.set_output_val(0, self.query)


class DQueryBuilder(NodeBase):
    """Build Query for Relational Database"""

    title = "DQ Builder"
    init_inputs = [
        NodeInputBP("target", dtype=dtypes.Data(default=["v4864"])),
        NodeInputBP("endpoint", dtype=dtypes.String(default="127.0.0.1")),
        NodeInputBP(" db param", dtype=dtypes.String(os.getcwd() + "/db_params.json")),
        NodeInputBP("start", dtype=dtypes.String(default="2022-07-11")),
        NodeInputBP(" end", dtype=dtypes.String(default="2022-07-12")),
        NodeInputBP("limit", dtype=dtypes.Integer(default=200)),
        NodeInputBP(" query"),
    ]
    init_outputs = [
        NodeOutputBP("dataframe"),
    ]

    def __init__(self, params):
        super().__init__(params)

        self.target = None
        self.ip = None
        self.start = None
        self.end = None
        self.limit = None
        self.query = None

    def update_event(self, inp=-1):

        self.target = self.input(0)
        self.ip = self.input(1)
        self.db_param = self.input(2)
        self.start = self.input(3)
        self.end = self.input(4)
        self.limit = self.input(5) if self.input(5) <= 1500 else 1500
        self.query = self.input(6) if self.input(6) is not None else None

        try:
            with open(self.db_param) as f:
                db_param = json.load(f)
        except Exception as f_error:
            print(f_error)

        client = InfluxDBClient(
            host=self.ip,
            port=8086,
            username=db_param["username"],
            password=db_param["password"],
            database=db_param["database"],
            ssl=False,
            verify_ssl=False,
        )

        if self.query is not None:
            print("Starting 😀")
            query_result = client.query(self.query)
            temp_result = query_result.raw["series"][0]["values"]
            df = pd.DataFrame(temp_result)
            print("No data found.") if len(query_result.raw["series"]) == 0 else print(
                "Query complete."
            )
        else:
            try:
                print("Starting ...")
                df = pd.DataFrame(
                    columns=["data_point", "db_time", "created_time", "values"]
                )
                for item in self.target:
                    print("Query in progress ...")
                    query_string = """SELECT tag_code,tag_value,ts FROM kafka_consumer 
WHERE ("host"='f26dht') AND ("tag_code"='%s') AND time >= '%s 00:00:00' 
AND time < '%s 00:00:00' ORDER BY time DESC LIMIT %i """ % (
                        item,
                        self.start,
                        self.end,
                        self.limit,
                    )

                    query_result = client.query(query_string)
                    print(query_string)
                    if len(query_result.raw["series"]) == 0:
                        print("Still trying ...")
                        query_string = """SELECT meta_id,max,created FROM kafka_consumer
WHERE ("meta_id"='%s') AND time >= '%s 00:00:00' AND time < '%s 00:00:00'
ORDER BY time DESC LIMIT %i""" % (
                            item,
                            self.start,
                            self.end,
                            self.limit,
                        )
                        query_result = client.query(query_string)
                        print(query_string)
                    print("No data found.") if len(
                        query_result.raw["series"]
                    ) == 0 else print("Query complete.")

                    temp_result = query_result.raw["series"][0]["values"]
                    temp_df = pd.DataFrame(
                        temp_result,
                        columns=["data_point", "db_time", "created_time", "values"],
                    )
                    df = pd.concat([df, temp_df], ignore_index=True)
            except Exception as e:
                print(e)
        self.set_output_val(0, df)


class SaveData(NodeBase):
    """Save dataframe to csv"""

    title = "Save Data"
    input_widget_classes = {"path input": widgets.PathInput}
    init_inputs = [
        NodeInputBP("data"),
        NodeInputBP(
            "path", add_data={"widget name": "path input", "widget pos": "below"}
        ),
    ]

    def __init__(self, params):
        super().__init__(params)

        self.active = False
        self.file_path = ""
        self.actions["make executable"] = {"method": self.action_make_executable}

    def view_place_event(self):
        self.input_widget(1).path_chosen.connect(self.path_chosen)

    def path_chosen(self, new_path):
        self.file_path = new_path
        self.update()

    def action_make_executable(self):
        self.create_input(type_="exec", insert=0)
        self.active = True

        del self.actions["make executable"]
        self.actions["make passive"] = {"method": self.action_make_passive}

    def action_make_passive(self):
        self.delete_input(0)
        self.active = False

        del self.actions["make passive"]
        self.actions["make executable"] = {"method": self.action_make_executable}

    def update_event(self, inp=-1):
        if not self.active or (self.active and inp == 0):
            df = self.input(0)
            df.to_csv(self.file_path, index=False)

    def get_state(self):
        return {"path": self.file_path}

    def set_state(self, data, version):
        self.file_path = data["path"]


export_nodes(
    ReadOntology,
    Watch,
    OntoData,
    IDBuilder,
    GQueryBuilder,
    SaveData,
    Select,
    DQueryBuilder,
)
