package yunogum.MetricCalculator;

import java.util.Map;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.tree.Tree;

import yunogum.AstUtils;
import yunogum.MetricRunner;
import yunogum.PythonFileData;

public  class DeletedIfMetrics extends IfMetrics{
    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int deletedIfStmts = 0;
        for(Tree t: classifier.getDeletedSrcs()){
            if(t.getType().name.equals(AstUtils.IF_STMT) ){
                if(fileData.isSrcNodeInExtendedRange(t) && fileData.checkIfInFunctionScope(t)){
                    deletedIfStmts++;
                    // MetricRunner.dlog((t.toTreeString()));
                    MetricRunner.dlog("deletion in extended range :\n" + t.toTreeString());
                }else{
                    MetricRunner.dlog("deletion out of range :\n" + t.toTreeString());
                }
            }
            
        }
        metrics.put("deletedIfStmts", deletedIfStmts);
    }



    public void putHeader(List<String> headers){
        headers.add("deletedIfStmts");
    }

}


