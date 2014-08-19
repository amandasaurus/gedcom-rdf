import rdflib
import gedcom
from rdflib.namespace import DC, FOAF, Namespace
from rdflib import RDF, Literal, BNode


def gedcom2rdf(gedcom_filename, rdf_filename):
    gedcomfile = gedcom.parse_filename(gedcom_filename)
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
                                

            
        


    with open(rdf_filename, 'w') as fp:
        fp.write(output_graph.serialize(format="turtle"))


gedcom2rdf('BUELL001.GED', 'buell.ttl')
#gedcom2rdf('sample.ged', 'sample.ttl')
