package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Hashtable;
import java.util.Iterator;
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

import yunogum.InsertAction;
import yunogum.PythonFileData;

public class AllMetricsCalculator extends MetricCalculator {
    public void putHeader(List<String> headers){
        //line deleted is a common case but it is hard to detect if entire line is deleted due to white space offsets
        //need to calc whitespae in line before considering 
        headers.add("MovedBlocksInIfConditions");

        headers.add("AddedOrUpdatedComments");

        headers.add("InsertedAssertConditions");

        headers.add("InsertedTryCatch");

        // headers.add("ModificationInsideCondtion");

        headers.add("UpdatedValueAssignments");

        headers.add("RemovedTryCatch");
        
        headers.add("UpdatedFuncArguments");


    } 

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        
        calcMovedBlocksInIfConditions(metrics,  results, classifier, fileData);
        
        calcAddedOrUpdatedComments(metrics,  results, classifier, fileData);
        
        calcInsertedAsssertConditions(metrics,  results, classifier, fileData);

        calcInsertedTryCatch(metrics,  results, classifier, fileData);

        // calcModificationInsideCondtion(metrics,  results, classifier, fileData);

        calcUpdatedValueAssignments(metrics,  results, classifier, fileData);

        calcRemovalTryCatch(metrics,  results, classifier, fileData);

        calcMismatchedFuncArguments(metrics,  results, classifier, fileData);
    }



    public static void calcMovedBlocksInIfConditions(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
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
                if(tDst != null){
                    if(tDst.getType().name.equals("if_stmt")){
                        for (Tree childTree : tDst.getChildren()) {
                            if(AstUtils.isTreeType(childTree, AstUtils.SUITE)){
                            
                            }else{
                                if(classifier.getMovedSrcs().contains(childTree)){
                                    MovedBlocksInIfConditions++;
                                }
                            }
                        }
                    }else{
                        System.out.println("if mapped to ???" + t + " " +tDst );
                    }
                }
            }
        }

        metrics.put("MovedBlocksInIfConditions", MovedBlocksInIfConditions);
        
        System.out.println(MovedBlocksInIfConditions);

    }


    private static int calcAddedOrUpdatedComments(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int updatedComments = 0;
        for (Tree t : classifier.getUpdatedSrcs()) {
            Tree dstTree = results.mappings.getDstForSrc(t);
            if (t.getType().toString().equals("string")//add this condition check before all trees in src (NOT DST)
            && fileData.isSrcNodeInExtendedRange(t) 
            && fileData.checkIfInFunctionScope(t))
                updatedComments++;
        }
        int addedComments = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().toString().equals("string")//add this condition check before all trees in dst (NOT SRC) 
            && fileData.isDstNodeInExtendedRange(t)) {
                addedComments++;
            }
        }
        metrics.put("AddedOrUpdatedComments", updatedComments + addedComments);
        return updatedComments + addedComments;
    }

    private static int calcInsertedAsssertConditions(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int insertedAsssertConditions = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().name.equals("assert_stmt")//add this condition check before all trees in dst (NOT SRC) 
            && fileData.isDstNodeInExtendedRange(t)) {
                insertedAsssertConditions++;
            }
        }
        metrics.put("InsertedAssertConditions", insertedAsssertConditions);
        return insertedAsssertConditions;
    }

    private static int calcInsertedTryCatch(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int InsertedTryCatch = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if ((t.getType().name.equals("try_stmt") || t.getType().name.equals("except_clause")) 
            //add this condition check before all trees in dst (NOT SRC) 
            && fileData.isDstNodeInExtendedRange(t)){
                InsertedTryCatch++;
            }

        }
        metrics.put("InsertedTryCatch", InsertedTryCatch);
        return InsertedTryCatch;
    }

    private static int calcModificationInsideCondtion(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int ModificationInsideCondtion = 0;
        // modified operators
        
        for (Tree t : classifier.getUpdatedSrcs()) {
            //CHECK IF_STMT 
            if (t.getType().name.equals("operator") 
                //add this condition check before all trees in src (NOT DST)
                && fileData.isSrcNodeInExtendedRange(t) 
                && fileData.checkIfInFunctionScope(t)) {
                ModificationInsideCondtion++;
            }
        }
        //added more conditions

        int added  = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            //CHECK IF_STMT 
            if (t.getType().name.equals("operator") 
                //add this condition check before all trees in dst (NOT SRC) 
                && fileData.isDstNodeInExtendedRange(t)) {
                ModificationInsideCondtion++;
            }
        }
        metrics.put("ModificationInsideCondtion", ModificationInsideCondtion);

        //check
        return ModificationInsideCondtion;
    }
    
    private static int calcUpdatedValueAssignments(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int UpdatedValueAssignments = 0;
        for (Tree t : classifier.getUpdatedDsts()) {
            if ((t.getType().name.equals("string") || t.getType().name.equals("number")) 
            //add this condition check before all trees in dst (NOT SRC) 
            && fileData.isDstNodeInExtendedRange(t)){
                UpdatedValueAssignments++;
            }
        }
        metrics.put("UpdatedValueAssignments", UpdatedValueAssignments);
        return UpdatedValueAssignments;
    }

    private static int calcRemovalTryCatch(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int deletedTryCatchStmts = 0;
        for (Tree t : classifier.getDeletedSrcs()) {
            if (t.getType().name.equals("try_stmt") //add this condition check before all trees in src (NOT DST)
            && fileData.isSrcNodeInExtendedRange(t) 
            && fileData.checkIfInFunctionScope(t)){
                deletedTryCatchStmts++;
            } else if (t.getType().name.equals("except_clause")) {
                deletedTryCatchStmts++;
            }
        }
        metrics.put("RemovedTryCatch", deletedTryCatchStmts);
        return deletedTryCatchStmts;
    }

    private static int calcMismatchedFuncArguments(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        int deletedParamsInDest = 0;
        for (Tree t : classifier.getDeletedSrcs()) {
            // System.out.println(t);
            if (t.getType().toString().equals("param")//add this condition check before all trees in src (NOT DST)
            && fileData.isSrcNodeInExtendedRange(t) 
            && fileData.checkIfInFunctionScope(t)) {
                deletedParamsInDest++;
            }
        }
        int insertedParamsInDest = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            // System.out.println(t);
            if (t.getType().toString().equals("param") //add this condition check before all trees in dst (NOT SRC) 
            && fileData.isDstNodeInExtendedRange(t)) {
                insertedParamsInDest++;
            }
        }
        metrics.put("UpdatedFuncArguments", deletedParamsInDest + insertedParamsInDest);

        return deletedParamsInDest + insertedParamsInDest;
    }


}
