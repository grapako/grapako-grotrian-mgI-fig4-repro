# src/grotrian_plotter/data_loader.py
import pandas as pd
import os
import pyodbc, sqlalchemy


def SQL_table(table, where='', columns='*', server='Local', database='AtmosphericModels4suoGPK'):
    ''' columns must be separated by commas as in a SQL query '''
    
    pyodbc.lowercase = False
    if server == 'Local':
        server = os.environ['COMPUTERNAME'] # Get your local server automatically
    else:
        server = server
    print(f"Getting data from {table} in {server}")
    
    conn = 'mssql+pyodbc:///?odbc_connect={}'.format('DRIVER={SQL Server};'
                                  'SERVER='+server+';'
                                  'DATABASE='+database+';'
                                  'uid=sa;pwd=1234Plantilla')
    
    engine = sqlalchemy.create_engine(conn)
    connection = engine.connect()
    
    table = f"SELECT {columns} FROM "+'['+database+']'+'.dbo.'+'['+table+'] '   
    query = table+where
#    print("\nQUERY:",query)
    # return pd.read_sql(query, connection) # TO FIND THE ERROR
    try:
        return pd.read_sql(query, connection)
    except:
        print('DATA from {} -> {} -> {}: NOT received'.format(server,database,table))
    # connection.close() # Closes automatically
    
# -----------------------------------------------------------------------------
def SQL_where(model=None,atom=None,ion=None,level=None,sublevel=None,Pi=None,
              lowerlevel=None,lowersublevel=None,upperlevel=None,
              uppersublevel=None,custom=None):
    filters = ['ModelIndex={}'.format(model),
                'AtomicNumber={}'.format(atom),
                'IonCharge={}'.format(ion),
                'LevelNumber={}'.format(level),
                'SublevelNumber={}'.format(sublevel),
                'LowerLevel={}'.format(lowerlevel),
                'LowerSublevel={}'.format(lowersublevel),
                'UpperLevel={}'.format(upperlevel),
                'UpperSublevel={}'.format(uppersublevel),
                'PointIndex={}'.format(Pi),
                f'{custom}']
    selected = [element for element in filters if 'None' not in element]
    return "WHERE "+" AND ".join(selected)


def read_table_from_file(path, usecols=None):
    """Read whitespace-separated table with pandas, return DataFrame.
    We try to load as strings first and then cast necessary cols where possible.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    # read flexibly; allow comments '#' too
    df = pd.read_csv(path, sep=r'\s+', comment='#', engine='python', dtype=str)
    if usecols:
        # keep only requested columns if present
        cols = [c for c in usecols if c in df.columns]
        df = df.loc[:, cols]
    return df


def fetch_levels_tables(database, atom, ion, levs,
                        file_level=None, file_sublevel=None):
    """Return Levels and LevelsSublevels DataFrames filtered for given levs.
    Si se pasan file_level y file_sublevel, se leen desde archivos locales.
    """
    levs_str = ','.join([str(l) for l in levs])

    if file_level and file_sublevel:
        # --- lectura desde archivos locales ---
        Levels_SQL = pd.read_csv(file_level, sep=r'\s+', comment='#', engine='python', dtype=str)
        LevelsSub_SQL = pd.read_csv(file_sublevel, sep=r'\s+', comment='#', engine='python', dtype=str)

        # Filtrar columnas relevantes si existen
        Levels_SQL = Levels_SQL.loc[:, [c for c in ['LevelNumber','FullConfig','ElectronConfig'] if c in Levels_SQL.columns]]
        LevelsSub_SQL = LevelsSub_SQL.loc[:, [c for c in ['LevelNumber','SublevelNumber','2J','ExcitationWaven'] if c in LevelsSub_SQL.columns]]

        # Convertir a numéricos donde aplique
        for col in ['LevelNumber','SublevelNumber','2J','ExcitationWaven']:
            if col in LevelsSub_SQL.columns:
                LevelsSub_SQL[col] = pd.to_numeric(LevelsSub_SQL[col], errors='coerce')
        if 'LevelNumber' in Levels_SQL.columns:
            Levels_SQL['LevelNumber'] = pd.to_numeric(Levels_SQL['LevelNumber'], errors='coerce')

        # Filtrar por levs
        Levels_SQL = Levels_SQL[Levels_SQL['LevelNumber'].isin(levs)]
        LevelsSub_SQL = LevelsSub_SQL[LevelsSub_SQL['LevelNumber'].isin(levs)]

        return Levels_SQL.reset_index(drop=True), LevelsSub_SQL.reset_index(drop=True)

    else:
        # --- lectura desde SQL (original) ---
        Levels_SQL = SQL_table('ModelAtomicIonLevel',
                               SQL_where(atom=atom, ion=ion) + f" AND LevelNumber IN ({levs_str})",
                               database=database).loc[:, ['LevelNumber','FullConfig','ElectronConfig']]
        LevelsSub_SQL = SQL_table('ModelAtomicIonLevelSublevel',
                                  SQL_where(atom=atom, ion=ion) + f" AND LevelNumber IN ({levs_str})",
                                  database=database).loc[:, ['LevelNumber','SublevelNumber','2J','ExcitationWaven']]
        return Levels_SQL, LevelsSub_SQL


def fetch_transitions(database, atom, ion, levs_str,
                      file_linefine=None):
    """Fetch transitions as list of rows.
    Si se pasa file_linefine, se lee desde archivo local.
    """
    if file_linefine:
        DB_trans = pd.read_csv(file_linefine, sep=r'\s+', comment='#', engine='python', dtype=str)
        DB_trans = DB_trans.loc[:, [c for c in ['LowerLevel','LowerSublevel','UpperLevel','UpperSublevel'] if c in DB_trans.columns]]
        for col in DB_trans.columns:
            DB_trans[col] = pd.to_numeric(DB_trans[col], errors='coerce')
        return DB_trans.values.tolist()
    else:
        DB_trans = SQL_table('ModelAtomicIonLineFine',
                             SQL_where(atom=atom, ion=ion) + f'AND UpperLevel IN ({levs_str})',
                             database=database).loc[:, ['LowerLevel','LowerSublevel','UpperLevel','UpperSublevel']]
        return DB_trans.values.tolist()
