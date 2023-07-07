package yunogum;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.io.Reader;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Hashtable;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.io.FileUtils;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.gen.SyntaxException;
import com.opencsv.*;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;  

public class DupeFileDetector {
    public static final boolean DEBUG =false;
    public static final boolean PRINT_TO_FILE =true;
    public static PrintStream ps;

    public static void dlog(String s){
        if(DEBUG)
            log(s);
    }

    public static void dlog(Object s){
        if(DEBUG)
            log(s);
    }
    public static void log(Object s){
        if(PRINT_TO_FILE)
            ps.println(s);
    }
    public static void logAll(String s){
        System.out.println(s);
        if(PRINT_TO_FILE)
            ps.println(s);
    }
    public static void main(String[] args) {
        Run.initClients();
        String testPath = "data/data_new";
        initialize();
        calcMetricsForCSV(testPath);
    }
    private static void initialize() {
        if(PRINT_TO_FILE){
            try{
                File file = new File(".temp");
                FileOutputStream fos = new FileOutputStream(file);
                ps = new PrintStream(fos);
            }catch(Exception e){
                System.out.println(e);
            }
        }
    }

    private static void calcMetricsForCSV(String csvPath) {
        String csv = csvPath+".csv";
        // Registry.Factory<? extends Client> client;
        try (
            BufferedReader reader = new BufferedReader(new FileReader(new File(csv)));
            CSVReader csvReader = new CSVReader(reader);
            CSVWriter writer = new CSVWriter(new FileWriter(csvPath+ "_metrics"+".csv"))
        ) {


            List<String[]> rows = csvReader.readAll();

           


            boolean isColumnLabelRow = true;//1st row is column labels

            int totalDupes = 0;
            int dupesInFalsePositive = 0; 
            int dupesInFunctional = 0; 
            int dupesInEvolve = 0; 
            int dupesInDiscuss = 0; 
            
            int numFalsePositive = 0; 
            int numFunctional = 0; 
            int numEvolve = 0; 
            int numDiscuss = 0; 

            List<String[]> dupeResults = new ArrayList<>(rows.size());
    
            for (int r = 0;r< rows.size();r++) {
                if(isColumnLabelRow){
                    isColumnLabelRow = false;
                    continue;
                }
                String[] row = rows.get(r);
                String category = row[2];

          

                // logAll("row: " + (r));
                String folderName = row[1];//1st col is the one with commentid which is the folder name
                // System.out.println("FolderName : " + folderName);
                
                File oldFolder = new File("Data New/"+folderName +"/Old");
                File[] oldFiles = oldFolder.listFiles();
                // log("oldFiles " + (oldFiles == null? "null":"notnull"));
                File oldFile = oldFiles != null && oldFiles.length > 0? oldFiles[0]: null;

                File newFolder = new File("Data New/"+folderName +"/New");

                File[] newFiles = newFolder.listFiles();
                // log("newFiles " + (newFiles == null? "null":"notnull"));
                File newFile = newFiles != null && newFiles.length > 0? newFiles[0]: null;
                
                boolean hasOldFile = oldFile != null;
                boolean hasNewFile = newFile != null;
                int numOldFiles = oldFiles != null ? oldFiles.length : 0;
                int numNewFiles = newFiles != null  ? newFiles.length: 0;
                
                if(numOldFiles > 1 || numNewFiles > 1)
                    throw new IOException("num oldiles" + numOldFiles + " numNewFiles " + numNewFiles );
                if(!hasOldFile && !hasNewFile)
                    throw new  IOException("not hasOldFile not hasNewFile" );
                if(!hasOldFile && hasNewFile){
                    //this should not be exception though fix later.
                    throw new  IOException("not has hasOldFile but hasNewFile");
                }
                if(hasOldFile && !hasNewFile){
                    newFile = oldFile;
                    System.out.println("hasOldFile && !hasNewFile : " + folderName + " " + category);
                }else{
                    System.out.println("normal : " + folderName + " " + category);
                }

                boolean isTwoEqual = FileUtils.contentEquals(oldFile, newFile);
                String srcFile = oldFile.getPath();
                String dstFile = newFile.getPath();
                
                dupeResults.add( new String[]{folderName,Integer.toString(isTwoEqual? 1 : 0) });

                if(isTwoEqual){
                    System.out.println("FolderName : " + folderName + " " + category);

                    System.out.println("Dupe: " + srcFile + " vs " + dstFile);
                    totalDupes++;
                    if(category.equals("False")){
                        dupesInFalsePositive++;
                    }else if(category.equals("EVOLVE")){
                        dupesInEvolve++;
                    }else if(category.equals("DISCUSS")){
                        dupesInDiscuss++;
                    }
                    else if(category.equals("FUNCTION")){
                        dupesInFunctional++;
                    }
                }
                if(category.equals("False")){
                    numFalsePositive++;
                }else if(category.equals("EVOLVE")){
                    numEvolve++;
                }else if(category.equals("DISCUSS")){
                    numDiscuss++;
                }
                else if(category.equals("FUNCTION")){
                    numFunctional++;
                }
            }
            System.out.println("numDupes " + totalDupes);
            System.out.println((100 * totalDupes/rows.size())+"% " );
            System.out.println("rows check " + (numFalsePositive + numEvolve + numDiscuss + numFunctional) + " vs " + rows.size());
            System.out.println((100.0f *dupesInFalsePositive / numFalsePositive)+"% dupesInFalsePositive " + dupesInFalsePositive + " / "+  (numFalsePositive));
            System.out.println((100.0f *dupesInEvolve / numEvolve)+"% dupesInEvolve " + dupesInEvolve + " / "+  (numEvolve));
            System.out.println((100.0f *dupesInDiscuss / numDiscuss)+"% dupesInDiscuss " + dupesInDiscuss + " / "+  (numDiscuss));
            System.out.println((100.0f *dupesInFunctional / numFunctional)+"% dupesInFunctional " + dupesInFunctional + " / "+  (numFunctional) );
            System.out.println((dupesInFalsePositive + dupesInEvolve + dupesInDiscuss +dupesInFunctional) == totalDupes? "total ok " : "total not ok");

            String dupeCSV = csvPath+"_dupe.csv";
            // Registry.Factory<? extends Client> client;
            try (
                CSVWriter dupWriter = new CSVWriter(new FileWriter(csvPath+"_dupe.csv"))
            ) {
                dupWriter.writeNext(new String[]{"CommentID", "isDupe"});
                dupWriter.writeAll(dupeResults);
            }
        }catch(Exception e){
            logAll("csv error" + e);
            e.printStackTrace();
        }
    }
}
