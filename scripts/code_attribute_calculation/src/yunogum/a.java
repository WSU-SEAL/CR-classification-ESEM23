package yunogum;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.actions.model.Move;
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

public class a {
    public static void main(String[] origArgs) {
        Options opts = new Options();
        String[] args = Option.processCommandLine(origArgs, opts);

        Run.initClients();

        Registry.Factory<? extends Client> client;
        if (args.length == 0) {
            System.err.println("No command given.");
            Run.displayHelp(System.err, opts);
        } else if ((client = Clients.getInstance().getFactory(args[0])) == null) {
            System.err.printf("Unknown sub-command '%s'.\n", args[0]);
            Run.displayHelp(System.err, opts);
        } else {
            try {

                PrintStream console = System.out;

                File file = new File(".temp");
                FileOutputStream fos = new FileOutputStream(file);
                PrintStream ps = new PrintStream(fos);
                System.setOut(ps);

                Run.initGenerators(); // registers the available parsers
                // String srcFile = "a.py";
                // String dstFile = "b.py";
                String srcFile = args[1];
                String dstFile = args[2];
                Diff results = Diff.compute(srcFile, dstFile);
                // TreeClassifier classifier = results.createRootNodesClassifier();//we'll miss
                // a lot of changes if we just get root ndoes that changed
                TreeClassifier classifier = results.createAllNodeClassifier();

                System.out.println(results.mappings.size());

                // for (Mapping m : results.mappings) {
                //     System.out.println(m.first + " \nmaps to:\n " + m.second);
                // }

                System.out.println("SRC---------------------------------");
                System.out.println(results.src);
                System.out.println("DST---------------------------------");
                System.out.println(results.dst);

                System.out.println("UpdatedSrcs " + classifier.getUpdatedSrcs().size());
                System.out.println("UpdatedDest " + classifier.getUpdatedDsts().size());
                System.out.println("MovedSrcs " + classifier.getMovedSrcs().size());
                System.out.println("MovedDest " + classifier.getMovedDsts().size());
                System.out.println("InsertedDest " + classifier.getInsertedDsts().size());
                System.out.println("DeletedSrc " + classifier.getDeletedSrcs().size());

                int anyInserted = classifier.getInsertedDsts().size();
                int anyDeleted = classifier.getDeletedSrcs().size();

                Map<String, Integer> metrics = new Hashtable<>();

                calcAddedOrUpdatedComments(classifier, results, metrics);
                calcInsertedAsssertConditions(classifier, metrics);
                calcInsertedTryCatch(classifier, metrics);
                calcRemovalTryCatch(classifier, metrics);
                calcMismatchedFuncArguments(classifier, metrics);
                calcUpdatedValueAssignments(classifier, metrics);
                calcModificationInsideCondtion(classifier, metrics);
                calcMovedBlocksInIfConditions(results, classifier, metrics);

                for (Map.Entry<String, Integer> entry : metrics.entrySet()) {
                    String key = entry.getKey();
                    int val = entry.getValue();
                    System.out.println(key + " : " + val);
                }

            } catch (Exception e) {
                System.out.println(e);
            }
        }
    }

    public static void calcMovedBlocksInIfConditions(Diff results, TreeClassifier classifier, Map<String, Integer> metrics) {
        int MovedBlocksInIfConditions = 0;
        boolean wasLastChildSuite = true;
        for(Tree t: results.src.getRoot().preOrder()){
            if(t.getType().name.equals("if_stmt")){
                int childNo = 0;
                for (Tree childTree : t.getChildren()) {
                    if(AstUtils.isTreeType(childTree, AstUtils.SUITE)){
                        wasLastChildSuite = true;
                        if(childNo == (t.getChildren().size() - 1 )){
                        
                        }
                    }else{
                        if(!wasLastChildSuite){
                            System.out.println("EXEPECTED NON-SUITE child to be followed by SUITE.");
                        }
                        wasLastChildSuite = false;
                    }
                    childNo++;
                }
                Tree tDst = results.mappings.getDstForSrc(t);
                if(tDst != null &&  tDst.getType().name.equals("if_stmt")){
                    for (Tree childTree : tDst.getChildren()) {
                        if(AstUtils.isTreeType(childTree, AstUtils.SUITE)){
                        
                        }else{
                            if(classifier.getMovedSrcs().contains(childTree)){
                                MovedBlocksInIfConditions++;
                            }
                        }
                    }
                }else{
                    System.out.println("if mapped to ???");
                }
            }
        }

        metrics.put("MovedBlocksInIfConditions", MovedBlocksInIfConditions);
        
        System.out.println(MovedBlocksInIfConditions);

    }


    private static int calcAddedOrUpdatedComments(TreeClassifier classifier, Diff results,
            Map<String, Integer> metrics) {
        int updatedComments = 0;
        for (Tree t : classifier.getUpdatedSrcs()) {
            Tree dstTree = results.mappings.getDstForSrc(t);
            if (t.getType().toString().equals("string"))
                updatedComments++;
        }
        int addedComments = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().toString().equals("string")) {
                addedComments++;
            }
        }
        metrics.put("AddedOrUpdatedComments", updatedComments + addedComments);
        return updatedComments + addedComments;
    }

    private static int calcInsertedAsssertConditions(TreeClassifier classifier, Map<String, Integer> metrics) {
        int insertedAsssertConditions = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().name.equals("assert_stmt")) {
                insertedAsssertConditions++;
            }
        }
        metrics.put("InsertedAssertConditions", insertedAsssertConditions);
        return insertedAsssertConditions;
    }

    private static int calcInsertedTryCatch(TreeClassifier classifier, Map<String, Integer> metrics) {
        int InsertedTryCatch = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().name.equals("try_stmt") || t.getType().name.equals("except_clause")) {
                InsertedTryCatch++;
            }

        }
        metrics.put("InsertedTryCatch", InsertedTryCatch);
        return InsertedTryCatch;
    }

    private static int calcModificationInsideCondtion(TreeClassifier classifier, Map<String, Integer> metrics) {
        int ModificationInsideCondtion = 0;
        // modified operators
        for (Tree t : classifier.getUpdatedSrcs()) {
            if (t.getType().name.equals("operator")) {
                ModificationInsideCondtion++;
            }
        }
        //added more conditions
        int added  = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            ModificationInsideCondtion++;
        }
        metrics.put("ModificationInsideCondtion", ModificationInsideCondtion);
        return ModificationInsideCondtion;
    }
    private static int calcUpdatedValueAssignments(TreeClassifier classifier, Map<String, Integer> metrics) {
        int UpdatedValueAssignments = 0;
        for (Tree t : classifier.getUpdatedDsts()) {
            if (t.getType().name.equals("string") || t.getType().name.equals("number")) {
                UpdatedValueAssignments++;
            }
        }
        metrics.put("UpdatedValueAssignments", UpdatedValueAssignments);
        return UpdatedValueAssignments;
    }

    private static int calcRemovalTryCatch(TreeClassifier classifier, Map<String, Integer> metrics) {
        int deletedTryCatchStmts = 0;
        for (Tree t : classifier.getDeletedSrcs()) {
            if (t.getType().name.equals("try_stmt")) {
                deletedTryCatchStmts++;
            } else if (t.getType().name.equals("except_clause")) {
                deletedTryCatchStmts++;
            }
        }
        metrics.put("RemovedTryCatch", deletedTryCatchStmts);
        return deletedTryCatchStmts;
    }

    private static int calcMismatchedFuncArguments(TreeClassifier classifier, Map<String, Integer> metrics) {
        int deletedParamsInDest = 0;
        for (Tree t : classifier.getDeletedSrcs()) {
            // System.out.println(t);
            if (t.getType().toString().equals("param")) {
                deletedParamsInDest++;
            }
        }
        int insertedParamsInDest = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            // System.out.println(t);
            if (t.getType().toString().equals("param")) {
                insertedParamsInDest++;
            }
        }
        metrics.put("UpdatedFuncArguments", deletedParamsInDest + insertedParamsInDest);

        return deletedParamsInDest + insertedParamsInDest;
    }

}