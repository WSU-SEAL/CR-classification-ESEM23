package yunogum;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.actions.model.Insert;
import com.github.gumtreediff.actions.model.TreeAddition;
import com.github.gumtreediff.actions.model.TreeInsert;
import com.github.gumtreediff.client.Client;
import com.github.gumtreediff.client.Clients;
import com.github.gumtreediff.client.Option;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.client.Run.Options;
import com.github.gumtreediff.gen.Registry;
import com.github.gumtreediff.gen.SyntaxException;
import com.github.gumtreediff.gen.TreeGenerators;
import com.github.gumtreediff.matchers.Mapping;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.tree.DefaultTree;
import com.github.gumtreediff.tree.Tree;
import com.github.gumtreediff.tree.TreeContext;

import yunogum.MetricCalculator.IfMetrics;

public class FileSplitter{
   

    
    public static void main(String[] origArgs) throws Exception{

        PrintStream console = System.out;
        File file = new File(".temp");
        FileOutputStream fos = new FileOutputStream(file);
        PrintStream ps = new PrintStream(fos);
        System.setOut(ps);

         // Options opts = new Options();
         Run.initClients();
         // String trainPath = "data/Train_new";
         // calcMetricsForCSV(trainPath);

        //  String commentID = "9fdfeff1_719b5072";
         String commentID = "9fdfeff1_a1915354";

         String folderName = commentID;
         File oldFolder = new File("Data New/"+folderName +"/Old");
         File[] oldFiles = oldFolder.listFiles();
         System.out.println("oldFiles " + (oldFiles == null? "null":"notnull"));
         File oldFile = oldFiles != null && oldFiles.length > 0? oldFiles[0]: null;

         File newFolder = new File("Data New/"+folderName +"/New");

         File[] newFiles = newFolder.listFiles();
         System.out.println("newFiles " + (newFiles == null? "null":"notnull"));
         File newFile = newFiles != null && newFiles.length > 0? newFiles[0]: null;
         
         boolean hasOldFile = oldFile != null;
         boolean hasNewFile = newFile != null;
         int numOldFiles = oldFiles != null ? oldFiles.length : 0;
         int numNewFiles = newFiles != null  ? newFiles.length: 0;
         try{
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
            }
            String srcFile = oldFile.getPath();
            String dstFile = newFile.getPath();

            // String folder = "TestingData/ElseInsertion/";
            // String srcFile = folder + "a.py";
            // String dstFile = folder +"b.py";

            // int lineNo = 7;
            int lineNo = 6853;
            
            splitFiles(srcFile, dstFile, lineNo);
            
            
            System.out.println("client");
            System.setOut(console);
            FileComparerClient.launchClient(srcFile, dstFile);
        }catch(SyntaxException se){
            System.out.println(se);
        }catch(Exception ioe){
            System.out.println(ioe);
        }

    }
    static void splitFiles(String srcFile, String dstFile,int lineNo) throws IOException{

        Diff diff = Diff.compute(srcFile, dstFile);
        TreeClassifier classifier = diff.createAllNodeClassifier();
        PythonFileData srcFileData = PythonFileData.parseFile(srcFile,dstFile, lineNo,  diff, classifier);
        System.out.println("src::::::: \n " + diff.src.getRoot().toTreeString());
        System.out.println("dst::::::: \n " + diff.dst.getRoot().toTreeString());


        System.out.println("inserted:::::::::::::::::");
        System.out.println("Extended: " + srcFileData.extendedNodeRangeStart + "," + srcFileData.extendedNodeRangeEnd );
        System.out.println("Line: " + srcFileData.lineOuterNodeStart + "," + srcFileData.lineOuterNodeEnd );
        for (Tree insertedTree : classifier.getInsertedDsts()) {
            System.out.println(insertedTree.toTreeString());

            if(srcFileData.isDstNodeInLineRange(insertedTree)){
                System.out.println("inserted within line rnage"  );
            }else{
                System.out.println("inserted outside line rnage");
            }

            if(srcFileData.isDstNodeInExtendedRange(insertedTree)){
                System.out.println("inserted within extended rnage"  );
            }else{
                System.out.println("inserted outside extended rnage");
            }
        }
        System.out.println("xxxxxxxxxxxxxxxxx\n\n\n\n\n");
        Map<String, Integer> metrics = new HashMap<>();
        // IfMetrics ifElseMetrics = new IfMetrics();
        // ifElseMetrics.calc(metrics, diff, classifier, srcFileData);
        for (String k : metrics.keySet()) {
            System.out.println(k+ " :  " + metrics.get(k));
        }

        System.out.println(srcFileData);
    }
}