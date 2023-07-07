package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.tree.Tree;

import yunogum.InsertAction;
import yunogum.PythonFileData;

public class LineMetric extends MetricCalculator {
    public void putHeader(List<String> headers){
        //line deleted is a common case but it is hard to detect if entire line is deleted due to white space offsets
        //need to calc whitespae in line before considering 
        headers.add("AnythingInLineMoved");
        headers.add("AnythingInLineUpdated");
        headers.add("AnythingInLineDeleted");
        headers.add("AnythingMovedIntoLine");
        headers.add("AnythingInsertedIntoLine");
        //the line range is not guaranteed to make a line
        headers.add("EntireLineMoved");
        headers.add("EntireLineDeleted");
    } 
    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int AnythingInLineMoved = 0;
        int AnythingInLineUpdated = 0;
        int AnythingInLineDeleted = 0;
        int AnythingMovedIntoLine = 0;
        int AnythingInsertedIntoLine = 0;
  
        boolean EntireLineDeleted = true;
        boolean LineParentMoved = false;
        //anything in line is likely already in same function scope so not worht checking
        for (Tree tree : fileData.treesInRangeOfLine) {
            //line char range overestimates but that's ok because we won't get anything OUTSIDE the line
            boolean inLineCharRange = tree.getPos() >= fileData.lineCharStart  && tree.getEndPos() <= fileData.lineCharEnd;
            
            if(classifier.getDeletedSrcs().contains(tree)){
                if(inLineCharRange){
                    AnythingInLineDeleted++;
                }
            }else{
                if(inLineCharRange){
                    EntireLineDeleted = false;
                }
            }

            if(classifier.getUpdatedSrcs().contains(tree)){
                if(inLineCharRange){
                    AnythingInLineUpdated++;
                }
            }

            if(classifier.getMovedSrcs().contains(tree)){
                if(inLineCharRange){
                    AnythingInLineMoved++;
                }
            }
        }

        
        for (Tree insertedDstTree : classifier.getInsertedDsts()) {
            InsertAction srcInsertion = fileData.dstTreeToSrcInsertActionMap.getOrDefault(insertedDstTree, null);
            //#TODO the insertion position is actually a arange
            //as nodes after the insertion postion could be deleted
            if(srcInsertion != null &&  srcInsertion.charPosition <= fileData.lineCharStart && srcInsertion.charPosition <= fileData.lineCharEnd){
                AnythingInsertedIntoLine++;
            }
        }

        for (Tree tree : classifier.getMovedSrcs()) {
            if(tree.getPos() <= fileData.lineCharStart && tree.getEndPos() >= fileData.lineCharEnd){
                LineParentMoved = true;
            }

            if(fileData.lineCharStart  <= tree.getPos() &&  tree.getEndPos() <= fileData.lineCharEnd ){
                AnythingMovedIntoLine++;
            }
        }
        
        EntireLineDeleted = EntireLineDeleted && (AnythingInLineDeleted > 0);

        metrics.put("AnythingInLineMoved", AnythingInLineMoved);
        metrics.put("AnythingInLineUpdated",AnythingInLineUpdated);
        metrics.put("AnythingInLineDeleted",AnythingInLineDeleted);
        metrics.put("AnythingMovedIntoLine",AnythingMovedIntoLine);
        metrics.put("AnythingInsertedIntoLine",AnythingInsertedIntoLine);
        metrics.put("EntireLineMoved",LineParentMoved?1:0);
        metrics.put("EntireLineDeleted",EntireLineDeleted?1:0);
    }
}
