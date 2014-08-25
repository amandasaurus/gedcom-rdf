import sys

import rdflib
import gedcom
from gedcom import Individual
from rdflib.namespace import DC, FOAF, Namespace
from rdflib import RDF, Literal, BNode, URIRef

BIO = Namespace("http://purl.org/vocab/bio/0.1/")

def gedcom2rdf_files(gedcom_filename, rdf_filename):
    gedcomfile = gedcom.parse_filename(gedcom_filename)

    output_graph = gedcom2rdf(gedcomfile)


    with open(rdf_filename, 'w') as fp:
        fp.write(output_graph.serialize(format="turtle"))

def gedcom2rdf(gedcomfile):

    gedcom_individuals = gedcomfile.individuals

    output_graph = rdflib.Graph()

    output_graph.bind("bio", BIO)
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
            output_graph.add( (person, BIO.Birth, birth_node) )
            output_graph.add( (birth_node, RDF.type, BIO.Birth) )
            output_graph.add( (birth_node, BIO.principal, person) )
            try:
                output_graph.add( (birth_node, DC.date, Literal(birth.date)) )
                output_graph.add( (birth_node, BIO.date, Literal(birth.date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (birth_node, BIO.place, Literal(birth.place)) )
            except IndexError:
                pass

        # death
        try:
            death = gedcom_individual.death
        except IndexError:
            pass
        else:
            death_node = BNode()
            output_graph.add( (person, BIO.Death, death_node) )
            output_graph.add( (death_node, RDF.type, BIO.Death) )
            output_graph.add( (death_node, BIO.principal, person) )
            try:
                output_graph.add( (death_node, DC.date, Literal(death.date)) )
                output_graph.add( (death_node, BIO.date, Literal(death.date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (death_node, BIO.place, Literal(death.place)) )
            except IndexError:
                pass

        # notes
        note = gedcom_individual.note
        if note:
            output_graph.add( (person, URIRef("note"), Literal(note)) )

        # nobile title
        title = gedcom_individual.title
        if title:
            output_graph.add( (person, BIO.NobleTitle, Literal(title)) )


    # Loop again, so every person has a node now
    for gedcomid, person in gedcomid_to_node.items():
        gedcom_individual = gedcomfile[gedcomid]
        father = gedcom_individual.father
        if father:
            output_graph.add( (person, BIO.father, gedcomid_to_node[father.id]) )
        mother = gedcom_individual.mother
        if mother:
            output_graph.add( (person, BIO.mother, gedcomid_to_node[mother.id]) )

    # loop over all the families and add in all the marriages
    for family in gedcomfile.families:
        if 'MARR' in family:
            partners = family.get_list("HUSB") + family.get_list("WIFE")
            if len(partners) == 0:
                continue
            marriage_node = BNode()
            output_graph.add( (marriage_node, RDF.type, BIO.Marriage) )
            for partner in partners:
                output_graph.add( (marriage_node, BIO.partner, gedcomid_to_node[partner.as_individual().id]) )

            try:
                output_graph.add( (marriage_node, DC.date, Literal(family['MARR'].date)) )
                output_graph.add( (marriage_node, BIO.date, Literal(family['MARR'].date)) )
            except IndexError:
                pass
            try:
                output_graph.add( (marriage_node, BIO.place, Literal(family['MARR'].place)) )
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
    personuri_to_gedcom = {}

    for person in rdf_graph.subjects(RDF.type, FOAF.Person):
        uri = person
        firstname = rdf_graph.value(uri, FOAF.givenName)
        lastname = rdf_graph.value(uri, FOAF.familyName)
        gender = rdf_graph.value(uri, FOAF.gender)
        individual = gedcomfile.individual()
        # Name
        if firstname or lastname:
            name = gedcomfile.element("NAME")
            individual.add_child_element(name)
            if firstname:
                firstname = firstname.value
                name.add_child_element(gedcomfile.element("GIVN", value=firstname))
            if lastname:
                lastname = lastname.value
                name.add_child_element(gedcomfile.element("SURN", value=lastname))

        # Gender
        if gender:
            gender = gender.value
            if gender == 'female':
                gender = 'F'
            elif gender == 'male':
                gender = 'M'
            else:
                raise NonGedcomRecongisedSex(rdfsex=gender)
            individual.add_child_element(gedcomfile.element('SEX', value=gender))

        # notes
        for note in rdf_graph.objects(uri, URIRef("note")):
            note = note.value
            if "\n" in note:
                subnotes = note.split("\n")
                note_node = gedcomfile.element("NOTE", value=subnotes[0])
                for subnote in subnotes[1:]:
                    note_node.add_child_element(gedcomfile.element("CONT", value=subnote))
            else:
                note_node = gedcomfile.element("NOTE", value=note)
            individual.add_child_element(note_node)

        # Title
        title = rdf_graph.value(uri, BIO.NobleTitle)
        if title:
            individual.add_child_element(gedcomfile.element("TITL", value=title))

        # Birth
        birth_node = rdf_graph.value(uri, BIO.Birth)
        if birth_node:
            birthdate = rdf_graph.value(birth_node, BIO.date)
            birthplace = rdf_graph.value(birth_node, BIO.place)
            gd_birth = gedcomfile.element("BIRT")
            individual.add_child_element(gd_birth)
            if birthdate:
                gd_birth.add_child_element(gedcomfile.element("DATE", value=birthdate))
            if birthplace:
                gd_birth.add_child_element(gedcomfile.element("PLAC", value=birthplace))

        # Death
        death_node = rdf_graph.value(uri, BIO.Death)
        if death_node:
            deathdate = rdf_graph.value(death_node, BIO.date)
            deathplace = rdf_graph.value(death_node, BIO.place)
            gd_death = gedcomfile.element("DEAT")
            individual.add_child_element(gd_death)
            if deathdate:
                gd_death.add_child_element(gedcomfile.element("DATE", value=deathdate))
            if deathplace:
                gd_death.add_child_element(gedcomfile.element("PLAC", value=deathplace))


        gedcomfile.add_element(individual)
        personuri_to_gedcom[uri] = individual

    print "All marriages"

    # try to figure out families
    # Simple families, 2 people
    # look for a marriage event between 2 people of different genders.
    marriage_uri_to_gedcom_family = {}

    for marriageuri in rdf_graph.subjects(RDF.type, BIO.Marriage):
        partners = list(rdf_graph.objects(marriageuri, BIO.partner))
        if len(partners) > 2:
            raise UnconvertableRDFGraph()

        genders = [rdf_graph.value(p, FOAF.gender) for p in partners]
        if genders == ['male', 'male'] or genders == ['female', 'female']:
            raise UnconvertableRDFGraph(uri=marriageuri)

        malepartneruri, femalepartneruri = None, None
        for partner, gender in zip(partners, genders):
            if gender == 'male':
                malepartneruri = partner
            elif gender == 'female':
                femalepartneruri = partner
            else:
                raise NonGedcomRecongisedSex(rdfsex=gender)

        print "Looking at marriage", malepartneruri

        family = gedcomfile.family()
        if malepartneruri:
            husb = personuri_to_gedcom[malepartneruri]
            family.add_child_element(gedcomfile.element("HUSB", value=husb.id))
        if femalepartneruri:
            wife = personuri_to_gedcom[femalepartneruri]
            family.add_child_element(gedcomfile.element("WIFE", value=wife.id))

        marr = gedcomfile.element("MARR")
        family.add_child_element(marr)

        date = rdf_graph.value(marriageuri, BIO.date)
        if date:
            marr.add_child_element(gedcomfile.element("DATE", value=date))
        place = rdf_graph.value(marriageuri, BIO.date)
        if place:
            marr.add_child_element(gedcomfile.element("PLAC", value=place))


        # id will be generated here
        gedcomfile.add_element(family)

        if malepartneruri:
            husb.add_child_element(gedcomfile.element("FAMS", value=family.id))
        if femalepartneruri:
            wife.add_child_element(gedcomfile.element("FAMS", value=family.id))

        marriage_uri_to_gedcom_family[marriageuri] = family

    # find simple families
    # Someone who's mother and father are married
    parents = rdf_graph.query("""
        SELECT ?marriageuri ?child ?father ?mother
        WHERE {
            ?marriageuri a bio:Marriage .
            ?childuri a foaf:Person .
            OPTIONAL { ?marriageuri bio:partner ?father .
                       ?father a foaf:Person ; foaf:gender 'male' .
                       ?mother bio:father ?father . }
            OPTIONAL { ?marriageuri bio:partner ?mother .
                       ?mother a foaf:Person ; foaf:gender 'female' .
                       ?child bio:mother ?mother . }
        """)
    for parents_row in parents:
        marriage, child, father, mother = parents_row
        if father is None and mother is None:
            # No good
            continue
        


    return gedcomfile

if __name__ == '__main__':
    gedcom2rdf_files(sys.argv[1], sys.argv[2])
