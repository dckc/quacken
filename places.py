#   Postal codes alphabetized by postal abbreviation (not by state)
#   Abbreviation     State
# tx http://en.wikipedia.org/wiki/U.S._postal_abbreviations
#    http://en.wikipedia.org/wiki/Canadian_province_postal_abbreviations
_States="""   AK           Alaska
   AL           Alabama
   AR           Arkansas
   AZ           Arizona
   CA           California
   CO           Colorado
   CT           Connecticut
   DE           Delaware
   FL           Florida
   GA           Georgia
   HI           Hawaii
   IA           Iowa
   ID           Idaho
   IL           Illinois
   IN           Indiana
   KS           Kansas
   KY           Kentucky
   LA           Louisiana
   MA           Massachusetts
   MD           Maryland
   ME           Maine
   MI           Michigan
   MN           Minnesota
   MO           Missouri
   MS           Mississippi
   MT           Montana
   NC           North Carolina
   ND           North Dakota
   NE           Nebraska
   NH           New Hampshire
   NJ           New Jersey
   NM           New Mexico
   NV           Nevada
   NY           New York
   OH           Ohio
   OK           Oklahoma
   OR           Oregon
   PA           Pennsylvania
   RI           Rhode Island
   SC           South Carolina
   SD           South Dakota
   TN           Tennessee
   TX           Texas
   UT           Utah
   VA           Virginia
   VT           Vermont
   WA           Washington
   WI           Wisconsin
   WV           West Virginia
   WY           Wyoming"""

_Provinces="""    AB Alberta
    BC British Columbia
    MB Manitoba
    NB New Brunswick
    NL Newfoundland and Labrador
    NS Nova Scotia
    NT Northwest Territories
    NU Nunavut
    ON Ontario
    PE Prince Edward Island
    QC Quebec
    SK Saskatchewan
    YT Yukon"""

Regions = dict([ln.strip().split(None, 1) for ln in
                (_States + _Provinces).split("\n")])

Localities = (
    ('IL', ['CHICAGO']),
    ('KS', ['STANLEY', 'OVERLAND PARK', 'SHAWNEE MISSION', 'MERRIAM', 'CASSODY']),
    ('MA', ['CAMBRIDGE']),
    ('MN', ['ALBERT LEA', 'STILLWATER', 'OAKDALE']),
    ('MO', ['KANSAS CITY', 'COLUMBIA', 'FENTON']),
    ('TX', ['AUSTIN']),
    ('QC', ['MONTREAL', 'ST BERNARD LA']),
    ('NY', ['PATTERSONVILL']),
    ('ON', ['NIAGARA FALLS']),
    ('OH', ['GENEVA']),
    ('NY', ['BUFFALO']),
    )
