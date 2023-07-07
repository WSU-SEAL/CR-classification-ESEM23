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

import yunogum.MetricCalculator.AllMetricsCalculator;
import yunogum.MetricCalculator.AnyDeletedMetrics;
import yunogum.MetricCalculator.AnyInsertedMetrics;
import yunogum.MetricCalculator.AnyMovedMetrics;
import yunogum.MetricCalculator.AnyUpdatedMetrics;
import yunogum.MetricCalculator.DeletedElseMetrics;
import yunogum.MetricCalculator.DeletedIfMetrics;
import yunogum.MetricCalculator.IfMetrics;
import yunogum.MetricCalculator.InsertedElseMetrics;
import yunogum.MetricCalculator.InsertedIfMetrics;
import yunogum.MetricCalculator.LineMetric;
import yunogum.MetricCalculator.MetricCalculator;
import yunogum.MetricCalculator.StringAssignment;
import yunogum.MetricCalculator.StringUpdate;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;  

public class MetricRunner {
    public static final boolean DEBUG =false;
    public static final boolean PRINT_TO_FILE =true;
    public static final boolean USE_FUNCTION_SCOPE =true;
    public static final int LINE_RANGE =10;
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
    public  static void initialize() {
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

        List<MetricCalculator> metricCalculators = new ArrayList<>();
        metricCalculators.add(new AnyInsertedMetrics());
        metricCalculators.add(new AnyDeletedMetrics());
        metricCalculators.add(new AnyMovedMetrics());
        metricCalculators.add(new AnyUpdatedMetrics());
        metricCalculators.add(new InsertedIfMetrics());
        metricCalculators.add(new DeletedIfMetrics());
        metricCalculators.add(new InsertedElseMetrics());
        metricCalculators.add(new DeletedElseMetrics());
        metricCalculators.add(new LineMetric());
        metricCalculators.add(new StringUpdate());
        metricCalculators.add(new StringAssignment());
        metricCalculators.add(new AllMetricsCalculator());

        // Registry.Factory<? extends Client> client;
        try (
            BufferedReader reader = new BufferedReader(new FileReader(new File(csv)));
            CSVReader csvReader = new CSVReader(reader);
            CSVWriter writer = new CSVWriter(new FileWriter(csvPath+ "_metrics" + (USE_FUNCTION_SCOPE? "functionscope": "")+".csv"))
        ) {


            List<String[]> rows = csvReader.readAll();

            ArrayList<String> headers = new ArrayList<>();
            headers.add("folderName");
            
            for (MetricCalculator calculator : metricCalculators) {
                calculator.putHeader(headers);
            }

            
            int postMetricsHeaderStartIndex = headers.size();
            headers.add("hasOldFile");
            headers.add("hasNewFile");
            headers.add("numOldFiles");
            headers.add("numNewFiles");
            headers.add("isDupe");
            headers.add("error");

            // String[] headers = metrics.keySet().toArray(new String[0]);
            writer.writeNext(headers.toArray(new String[0]));
            boolean isColumnLabelRow = true;//1st row is column labels
            int r = 0;

            // if(DEBUG){
            //     r = 44;
            // }
            logAll(rows.size()+ "");
            for (;r< rows.size();r++) {
                if(isColumnLabelRow){
                    isColumnLabelRow = false;
                    continue;
                }
                String[] row = rows.get(r);
                if(DEBUG && r > 20){
                    logAll("BREAK");
                    break;
                }
                logAll("row: " + (r));
                String folderName = row[1];//1st col is the one with commentid which is the folder name
                System.out.println("FolderName : " + folderName);
                
                File oldFolder = new File("Data New/"+folderName +"/Old");
                File[] oldFiles = oldFolder.listFiles();
                log("oldFiles " + (oldFiles == null? "null":"notnull"));
                File oldFile = oldFiles != null && oldFiles.length > 0? oldFiles[0]: null;

                File newFolder = new File("Data New/"+folderName +"/New");

                File[] newFiles = newFolder.listFiles();
                log("newFiles " + (newFiles == null? "null":"notnull"));
                File newFile = newFiles != null && newFiles.length > 0? newFiles[0]: null;
                
                boolean hasOldFile = oldFile != null;
                boolean hasNewFile = newFile != null;
                boolean isDupe = hasOldFile && hasNewFile && FileUtils.contentEquals(oldFile, newFile);
                int numOldFiles = oldFiles != null ? oldFiles.length : 0;
                int numNewFiles = newFiles != null  ? newFiles.length: 0;
                String error = null;

                Map<String, Integer> metrics = new LinkedHashMap<>();
                String[] metricRow = new String[headers.size()];
                try{
                    if(numOldFiles > 1 || numNewFiles > 1)
                        throw new IOException("num oldFiles" + numOldFiles + " numNewFiles " + numNewFiles );
                    if(!hasOldFile && !hasNewFile)
                        throw new  IOException("not hasOldFile not hasNewFile" );
                    if(!hasOldFile && hasNewFile){
                        //this should not be exception though fix later.
                        throw new  IOException("not has hasOldFile but hasNewFile");
                    }
                    if(hasOldFile && !hasNewFile){
                        newFile = oldFile;
                    }


                    String srcFile = oldFile.getPath();
                    String dstFile = newFile.getPath();
                    int lineNo = (int)((float) Float.valueOf(row[6]));
                    
                      
                    Diff results = Diff.compute(srcFile, dstFile);
                    // TreeClassifier classifier = results.createRootNodesClassifier();//we'll miss a lot of changes if we just get root ndoes that changed
                    TreeClassifier classifier = results.createAllNodeClassifier();
                    PythonFileData fileData = PythonFileData.parseFile(srcFile,dstFile, lineNo, results, classifier);
  
                    
                    logAll(fileData.toString());

                    for (MetricCalculator calculator : metricCalculators) {
                        calculator.calc(metrics,results, classifier, fileData);
                    }
                    

                    //#TODO use this as a metric 
                    metrics.put("hasOldFile", hasOldFile ? 1 : 0);
                    metrics.put("hasNewFile", hasNewFile ? 1 : 0);

                    metrics.put("numOldFiles",numOldFiles);
                    metrics.put("numNewFiles",numNewFiles);
                    metrics.put("isDupe", isDupe? 1: 0);
                }catch(SyntaxException se){

                    metrics.put("hasOldFile", hasOldFile ? 1 : 0);
                    metrics.put("hasNewFile", hasNewFile ? 1 : 0);

                    metrics.put("numOldFiles",numOldFiles);
                    metrics.put("numNewFiles",numNewFiles);
                    metrics.put("isDupe", isDupe? 1: 0);
                    error = "syntax";
                    System.out.println(error);
                }catch(IOException ioe){
                    System.out.println(ioe);
                    metrics.put("hasOldFile", hasOldFile ? 1 : 0);
                    metrics.put("hasNewFile", hasNewFile ? 1 : 0);

                    metrics.put("numOldFiles",numOldFiles);
                    metrics.put("numNewFiles",numNewFiles);
                    metrics.put("isDupe", isDupe? 1: 0);
                    error = ioe.toString();
                }

                metricRow[0] = folderName;
                for(int i = 1; i < headers.size();i++){
                    metricRow[i] = Integer.toString(metrics.getOrDefault(headers.get(i), 0));
                    // System.out.print(headers.get(i) +  metricRow[i]);
                }
                // System.out.println("");
                
                if(error != null){
                    for (int i = 1; i < postMetricsHeaderStartIndex -1; i++) {
                        metricRow[i] = Integer.toString(-1);
                    }
                }
                metricRow[metricRow.length -1] = error;
                writer.writeNext(metricRow);

                // if(DEBUG && isDupe){
                //     break;
                // }
            }
        }catch(Exception e){
            logAll("csv error" + e);
            e.printStackTrace();
        }
    }
}
