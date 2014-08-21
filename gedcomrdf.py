import sys

import rdflib
import gedcom
from gedcom import Individual
from rdflib.namespace import DC, FOAF, Namespace
from rdflib import RDF, Literal, BNode


def gedcom2rdf_files(gedcom_filename, rdf_filename):
    gedcomfile = gedcom.parse_filename(gedcom_filename)

    output_graph = gedcom2rdf(gedcomfile)


    with open(rdf_filename, 'w') as fp:
        fp.write(output_graph.serialize(format="turtle"))

def gedcom2rdf(gedcomfile):

    gedcom_individuals = gedcomfile.individuals

    output_graph = rdflib.Graph()

    bio = Namespace("http://purl.org/vocab/bio/0.1/")
    output_graph.bind("bio", bio)
    output_graph.bind("foaf", FOAF)

    gedcomid_to_node = {}

    for gedcom_individual in gedcom_individuals:
        person = BNode()
        output_graph.add( (person, RDF.type, FOAF.Person) )

        gedcomid_to_node[gedcom_individual.id] = person

        firstname, lastname = gedcom_individual.name
        if firstname:
            output_graph.add( (person, FOAF.givenName, Literal(firstname) ) )
        if lastname:
            output_graph.add( (person, FOAF.familyName, Literal(lastname) ) )

        try:
            gender = gedcom_individual.gender
            if gender.lower() == 'f':
                gender = 'female'
            elif gender.lower() == 'm':
                gender = 'male'
            output_graph.add( (person, FOAF.gender, Literal(gender)) )
        except IndexError:
            pass

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


    # Loop again, so every person has a node now
    for gedcomid, person in gedcomid_to_node.items():
        gedcom_individual = gedcomfile[gedcomid]
        father = gedcom_individual.father
        if father:
            output_graph.add( (person, bio.father, gedcomid_to_node[father.id]) )
        mother = gedcom_individual.mother
        if mother:
            output_graph.add( (person, bio.mother, gedcomid_to_node[mother.id]) )

    # loop over all the families and add in all the marriages
    for family in gedcomfile.families:
        if 'MARR' in family:
            partners = family.get_list("HUSB") + family.get_list("WIFE")
            if len(partners) == 0:
                continue
            marriage_node = BNode()
            output_graph.add( (marriage_node, RDF.type, bio.Marriage) )
            for partner in partners:
                output_graph.add( (marriage_node, bio.partner, gedcomid_to_node[partner.as_individual().id]) )

            try:
                output_graph.add( (marriage_node, DC.date, Literal(family['MARR'].date)) )
                output_graph.add( (marriage_node, bio.date, Literal(family['MARR'].date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (marriage_node, bio.place, Literal(family['MARR'].place)) )
            except IndexError:
                pass

    return output_graph

class UnconvertableRDFGraph(Exception):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.kwargs = kwargs

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.kwargs))

class NonGedcomRecongisedSex(UnconvertableRDFGraph):
    pass

def rdf2gedcom(rdf_graph):
    gedcomfile = gedcom.GedcomFile()
    # all individuals
    people = rdf_graph.query("""
        SELECT ?personuri ?firstname ?lastname ?gender
        WHERE {
            ?personuri a foaf:Person
            OPTIONAL { ?personuri foaf:givenName ?firstname }
            OPTIONAL { ?personuri foaf:familyName ?lastname }
            OPTIONAL { ?personuri foaf:gender ?gender }
        }""")

    personuri_to_gedcom = {}

    for person in people:
        uri, firstname, lastname, gender = person
            # use .value to turn rdf Literals in strings
        firstname = firstname.value
        lastname = lastname.value
        gender = gender.value
        individual = gedcomfile.individual()
        if firstname or lastname:
            name = gedcomfile.element("NAME")
            individual.add_child_element(name)
            if firstname:
                name.add_child_element(gedcomfile.element("GIVN", value=firstname))
            if lastname:
                name.add_child_element(gedcomfile.element("SURN", value=lastname))
        if gender:
            if gender == 'female':
                gender = 'F'
            elif gender == 'male':
                gender = 'M'
            else:
                raise NonGedcomRecongisedSex(rdfsex=gender)
            individual.add_child_element(gedcomfile.element('SEX', value=gender))

        gedcomfile.add_element(individual)
        personuri_to_gedcom[uri] = individual

    # try to figure out families
    # Simple families, 2 people
    # look for a marriage event between 2 people of different genders.
    marriages = rdf_graph.query("""
        SELECT ?marriageuri ?malepartneruri ?femalepartneruri ?date ?place
        WHERE {
            ?marriageuri a bio:Marriage ;
                bio:partner ?malepartneruri , ?femalepartneruri .
            ?malepartneruri a foaf:Person ; foaf:gender 'male' .
            ?femalepartneruri a foaf:Person ; foaf:gender 'female' .
            OPTIONAL { ?marriageuri bio:date ?date . }
            OPTIONAL { ?marriageuri bio:place ?place . }
        }""")

    for marriage in marriages:
        marriageuri, malepartneruri, femalepartneruri, date, place = marriage
        #date, place = date.value if date else N, place.value

        family = gedcomfile.family()
        family.add_child_element(gedcomfile.element("HUSB", value=personuri_to_gedcom[malepartneruri].id))
        family.add_child_element(gedcom.(value=personuri_to_gedcom[femalepartneruri].id))

        gedcomfile.add_element(family)

    return gedcomfile

if __name__ == '__main__':
    gedcom2rdf_files(sys.argv[1], sys.argv[2])
