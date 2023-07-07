package yunogum;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;

import java.awt.Toolkit;
import java.awt.datatransfer.DataFlavor;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.client.Client;
import com.github.gumtreediff.client.Clients;
import com.github.gumtreediff.client.Option;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.client.Run.Options;
import com.github.gumtreediff.gen.Registry;
import com.github.gumtreediff.gen.TreeGenerators;
import com.github.gumtreediff.matchers.Mapping;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.tree.DefaultTree;
import com.github.gumtreediff.tree.Tree;
import com.opencsv.CSVReader;
import com.opencsv.CSVWriter;
public class FileComparerClient {
    public static void launchClient(String srcFile, String dstFile){
        String command = "webdiff";
        Registry.Factory<? extends Client> client = Clients.getInstance().getFactory(command);

        Run.initGenerators(); // registers the available parsers

        if (client == null) {
            System.err.printf("Unknown sub-command '%s'.\n", "webdiff");
        } else {
            Run.startClient(command, client, new String[]{srcFile, dstFile});
        }
    }


    public static String readClipboard() throws Exception {
        return (String) Toolkit.getDefaultToolkit().getSystemClipboard().getData(DataFlavor.stringFlavor);
    }
    public static void main(String[] origArgs) {
        Options opts = new Options();
        String[] args = Option.processCommandLine(origArgs, opts);

        Run.initClients();

        // String folder = "TestingData/ChildMapper/";
        // String folder = "TestingData/ElseInsertion/";
        String folderName = null;
        String srcFile = null;
        String dstFile = null;
        

        if(origArgs.length >= 1 ){
            System.out.println(origArgs[0]);
            folderName = origArgs[0];
        }else{
            try{
                folderName = readClipboard();
                System.out.println("folderName: " + folderName);
            }catch (Exception e){
                System.out.println("clipboard exception" + e);
                return;
            }
    
        }

        File oldFolder = new File("Data New/"+folderName +"/Old");
        File[] oldFiles = oldFolder.listFiles();
        System.out.println("oldFiles " + (oldFiles != null && oldFiles.length > 0? "notnull":"null"));

        File oldFile = oldFiles != null && oldFiles.length > 0? oldFiles[0]: null;
        File newFolder = new File("Data New/"+folderName +"/New");

        File[] newFiles = newFolder.listFiles();
        System.out.println("newFiles " + ((newFiles != null && newFiles.length > 0)? "notnull":"null"));
        File newFile = newFiles != null && newFiles.length > 0? newFiles[0]: null;
        
        boolean hasOldFile = oldFile != null;
        boolean hasNewFile = newFile != null;

        if(!hasOldFile && !hasNewFile){
            System.out.println("no files " + hasOldFile + hasNewFile);
            return;
        }
        else if(hasOldFile && !hasNewFile){
            newFile = oldFile;
        }else if(!hasOldFile && hasNewFile){
            oldFile = newFile;
        }
        String testPath = "data/data_new";
        String csv = testPath+".csv";
        try (
            BufferedReader reader = new BufferedReader(new FileReader(new File(csv)));
            CSVReader csvReader = new CSVReader(reader);
            CSVWriter writer = new CSVWriter(new FileWriter(testPath+ "_metrics"+".csv"))
        ) {
            boolean isColumnLabelRow = true;

            List<String[]> rows = csvReader.readAll();
            int numDiscuss = 0; 
            for (int r=0;r< rows.size();r++) {
                if(isColumnLabelRow){
                    isColumnLabelRow = false;
                    continue;
                }
                String[] row = rows.get(r);
                if(row[1].equals(folderName)){
                    String category = row[2];
                    System.out.println("category: " + category);
                    break;
                }

            }

        }catch(Exception e){
            logAll("csv error" + e);
            e.printStackTrace();
        }

        srcFile = oldFile.getPath();
        dstFile = newFile.getPath();
        
        String command = "webdiff";
        Registry.Factory<? extends Client> client = Clients.getInstance().getFactory(command);

        if (client == null) {
            System.err.printf("Unknown sub-command '%s'.\n", "webdiff");
            Run.displayHelp(System.err, opts);
        } else {
            try{

                PrintStream console = System.out;

 

                Run.initGenerators(); // registers the available parsers


                Diff results = Diff.compute(srcFile, dstFile);
                
                Run.startClient(command, client, new String[]{srcFile, dstFile});
            }catch(Exception e){
                System.out.println("error" + e);
            }
        }
    }


    private static void logAll(String string) {
    }
}
