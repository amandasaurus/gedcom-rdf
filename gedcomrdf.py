import rdflib
import gedcom
from rdflib.namespace import DC, FOAF, Namespace
from rdflib import RDF, Literal, BNode


def gedcom2rdf(gedcom_filename, rdf_filename):
    gedcomfile = gedcom.Gedcom(gedcom_filename)
    gedcom_individuals = [i for i in gedcomfile.element_list() if i.is_individual()]

    output_graph = rdflib.Graph()

    bio = Namespace("http://purl.org/vocab/bio/0.1/")
    output_graph.bind("bio", bio)
    output_graph.bind("foaf", FOAF)

    for gedcom_individual in gedcom_individuals:
        person = BNode()
        output_graph.add( (person, RDF.type, FOAF.Person) )
        firstname, lastname = gedcom_individual.name()
        if firstname:
            output_graph.add( (person, FOAF.givenName, Literal(firstname) ) )
        if lastname:
            output_graph.add( (person, FOAF.familyName, Literal(lastname) ) )

        # Birth
        dob, place_of_birth = gedcom_individual.birth()
        if dob or place_of_birth:
            birth_node = BNode()
            output_graph.add( (person, bio.Birth, birth_node) )
            output_graph.add( (birth_node, RDF.type, bio.Birth) )
            output_graph.add( (birth_node, bio.principal, person) )
        if dob:
            output_graph.add( (birth_node, DC.date, Literal(dob)) )
            output_graph.add( (birth_node, bio.date, Literal(dob)) )
        if place_of_birth:
            output_graph.add( (birth_node, bio.place, Literal(place_of_birth)) )

        # Death
        death_date, place_of_death = gedcom_individual.death()
        if death_date or place_of_death:
            death_node = BNode()
            output_graph.add( (person, bio.Death, death_node) )
            output_graph.add( (death_node, RDF.type, bio.Death) )
            output_graph.add( (death_node, bio.principal, person) )
        if death_date:
            output_graph.add( (death_node, DC.date, Literal(death_date)) )
            output_graph.add( (death_node, bio.date, Literal(death_date)) )



    with open(rdf_filename, 'w') as fp:
        fp.write(output_graph.serialize(format="turtle"))


gedcom2rdf('BUELL001.GED', 'buell.ttl')
