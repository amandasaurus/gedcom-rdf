import rdflib
import gedcom
from rdflib.namespace import DC, FOAF, Namespace
from rdflib import RDF, Literal, BNode


def gedcom2rdf(gedcom_filename, rdf_filename):
    with open(gedcom_filename) as fp:
        gedcomfile = gedcom.parse(fp)
    gedcom_individuals = gedcomfile.individuals

    output_graph = rdflib.Graph()

    bio = Namespace("http://purl.org/vocab/bio/0.1/")
    output_graph.bind("bio", bio)
    output_graph.bind("foaf", FOAF)

    for gedcom_individual in gedcom_individuals:
        person = BNode()
        output_graph.add( (person, RDF.type, FOAF.Person) )
        firstname, lastname = gedcom_individual.name
        if firstname:
            output_graph.add( (person, FOAF.givenName, Literal(firstname) ) )
        if lastname:
            output_graph.add( (person, FOAF.familyName, Literal(lastname) ) )

        # Birth
        try:
            birth = gedcom_individual.birth
        except IndexError:
            pass
        else:
            birth_node = BNode()
            output_graph.add( (person, bio.Birth, birth_node) )
            output_graph.add( (birth_node, RDF.type, bio.Birth) )
            output_graph.add( (birth_node, bio.principal, person) )
            try:
                output_graph.add( (birth_node, DC.date, Literal(birth.date)) )
                output_graph.add( (birth_node, bio.date, Literal(birth.date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (birth_node, bio.place, Literal(birth.place)) )
            except IndexError:
                pass

        # death
        try:
            death = gedcom_individual.death
        except IndexError:
            pass
        else:
            death_node = BNode()
            output_graph.add( (person, bio.Death, death_node) )
            output_graph.add( (death_node, RDF.type, bio.Death) )
            output_graph.add( (death_node, bio.principal, person) )
            try:
                output_graph.add( (death_node, DC.date, Literal(death.date)) )
                output_graph.add( (death_node, bio.date, Literal(death.date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (death_node, bio.place, Literal(death.place)) )
            except IndexError:
                pass


    with open(rdf_filename, 'w') as fp:
        fp.write(output_graph.serialize(format="turtle"))


gedcom2rdf('BUELL001.GED', 'buell.ttl')
