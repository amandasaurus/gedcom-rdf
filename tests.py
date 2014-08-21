import unittest
import gedcomrdf
import gedcom
import rdflib

# Sample GEDCOM file from Wikipedia
GEDCOM_FILE = """
0 HEAD
1 SOUR Reunion
2 VERS V8.0
2 CORP Leister Productions
1 DEST Reunion
1 DATE 11 FEB 2006
1 FILE test
1 GEDC
2 VERS 5.5
1 CHAR MACINTOSH
0 @I1@ INDI
1 NAME Bob /Cox/
1 SEX M
1 FAMS @F1@
1 CHAN
2 DATE 11 FEB 2006
0 @I2@ INDI
1 NAME Joann /Para/
1 SEX F
1 FAMS @F1@
1 CHAN
2 DATE 11 FEB 2006
0 @I3@ INDI
1 NAME Bobby Jo /Cox/
1 SEX M
1 FAMC @F1@
1 CHAN
2 DATE 11 FEB 2006
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
1 CHIL @I3@
0 TRLR
"""

SAMPLE_RDF="""
@prefix bio: <http://purl.org/vocab/bio/0.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] a bio:Marriage ;
    bio:partner _:N0e849430a8f04c35b09ca75bf1d57a28,
            _:N5a9ae49ead8f4fedb313e1eb889b9501 .

[] a foaf:Person ;
    bio:father _:N5a9ae49ead8f4fedb313e1eb889b9501 ;
    bio:mother _:N0e849430a8f04c35b09ca75bf1d57a28 ;
    foaf:familyName "Cox" ;
    foaf:gender "male" ;
    foaf:givenName "Bobby Jo" .

_:N0e849430a8f04c35b09ca75bf1d57a28 a foaf:Person ;
    foaf:familyName "Para" ;
    foaf:gender "female" ;
        foaf:givenName "Joann" .

_:N5a9ae49ead8f4fedb313e1eb889b9501 a foaf:Person ;
    foaf:familyName "Cox" ;
    foaf:gender "male" ;
    foaf:givenName "Bob" .

"""


class Gedcom2RDFTestCase(unittest.TestCase):

    def testSimpleFileConvert(self):
        gedcomfile = gedcom.parse(GEDCOM_FILE)
        rdf_graph = gedcomrdf.gedcom2rdf(gedcomfile)

        # Since BNodes might be used, we'll query it with SPARQL
        results = list(rdf_graph.query("SELECT ?bob WHERE { ?bob a foaf:Person ; foaf:gender 'male' ; foaf:givenName 'Bob' ; foaf:familyName 'Cox' }"))
        self.assertEqual(len(results), 1)
        bob_node = results[0][0]

        results = list(rdf_graph.query("SELECT ?joann WHERE { ?joann a foaf:Person ; foaf:gender 'female' ; foaf:givenName 'Joann' ; foaf:familyName 'Para' }"))
        self.assertEqual(len(results), 1)
        joann_node = results[0][0]

        results = list(rdf_graph.query("SELECT ?bobby_jo WHERE { ?bobby_jo a foaf:Person ; foaf:gender 'male' ; foaf:givenName 'Bobby Jo' ; foaf:familyName 'Cox' }"))
        self.assertEqual(len(results), 1)
        bobby_jo_node = results[0][0]

        # ensure these are all different uris
        self.assertNotEqual(bob_node, joann_node)
        self.assertNotEqual(bob_node, bobby_jo_node)
        self.assertNotEqual(joann_node, bobby_jo_node)

        self.assertTrue(rdf_graph.query("ASK { ?bobby_jo bio:father ?bob }", initBindings={'bobby_jo': bobby_jo_node, 'bob': bob_node }))
        self.assertTrue(rdf_graph.query("ASK { ?bobby_jo bio:mother ?joann }", initBindings={'joann': joann_node, 'bobby_jo': bobby_jo_node }))

        self.assertTrue(rdf_graph.query("ASK { ?marriage bio:partner ?bob, ?joann . }", initBindings={'joann': joann_node, 'bob': bob_node }))
        
def one_matching(list, predicate):
    """Return the element in `list` which matches `predicate`. :raises ValueError: if 0 or more than one elements of `list` match `predicate`"""
    matches = [el for el in list if predicate(el)]
    if len(matches) != 1:
        raise ValueError("{0} != 1 elements matched, Matching: {1}".format(len(matches), repr(matches)[:100]))
    else:
        return matches[0]

class RDF2GedcomTestCase(unittest.TestCase):
    def testSimple(self):
        rdf_graph = rdflib.Graph()
        rdf_graph.parse(data=SAMPLE_RDF, format="turtle")

        gedcomfile = gedcomrdf.rdf2gedcom(rdf_graph)
        individuals = list(gedcomfile.individuals)
        self.assertEqual(len(individuals), 3)

        # Order is not guaranted to be the same.
        bob = one_matching(individuals, lambda i: i.name == ('Bob', 'Cox'))
        bobby_jo = one_matching(individuals, lambda i: i.name == ('Bobby Jo', 'Cox'))
        joann = one_matching(individuals, lambda i: i.name == ('Joann', 'Para'))
        self.assertTrue(bob.is_male)
        self.assertTrue(bobby_jo.is_male)
        self.assertTrue(joann.is_female)

        # Families
        families = list(gedcomfile.families)
        self.assertEqual(len(families), 1)
        family = families[0]
        self.assertEqual(len(family.partners), 2)
        self.assertEqual(family.partners[0].as_individual(), bob)


if __name__ == '__main__':
    unittest.main()
