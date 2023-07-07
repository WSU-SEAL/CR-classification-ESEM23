package yunogum;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
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
import com.github.gumtreediff.tree.TreeContext;
public class CodeCommentTest {
    public static void main(String[] origArgs) {
        Options opts = new Options();
        String[] args = Option.processCommandLine(origArgs, opts);

        Run.initClients();
        MetricRunner.initialize();
        Registry.Factory<? extends Client> client;
        try {

            // File file = new File(".temp");
            // FileOutputStream fos = new FileOutputStream(file);
            // PrintStream ps = new PrintStream(fos);
            // System.setOut(ps);

            Run.initGenerators(); // registers the available parsers
            String srcFile = "TestingData/ElseInsertion/a.py";
            String dstFile = "TestingData/ElseInsertion/b.py";
            // String srcFile = args[1];
            // String dstFile = args[2];
            Map<String, Integer> metrics = new Hashtable<>();
            Diff results = Diff.compute(srcFile, dstFile);
            // TreeClassifier classifier = results.createRootNodesClassifier();//we'll miss
            // a lot of changes if we just get root ndoes that changed
            TreeClassifier classifier = results.createAllNodeClassifier();
            PythonFileData fileData = PythonFileData.parseFile(srcFile,dstFile, 0, results, classifier);
            // Set<Tree> deletedSrcs = classifier.getDeletedSrcs();
            Set<Tree> inserted = classifier.getInsertedDsts();
            MetricRunner.log(results.src.getRoot().toTreeString());
            System.out.println(inserted);
            // for(Mapping m: results.mappings ){
            // MetricRunner.dlog(m.first + " \nmaps to:\n " + m.second);
            // }

            calc(metrics, results, classifier, fileData);

            for (Map.Entry<String, Integer> entry : metrics.entrySet()) {
                String key = entry.getKey();
                int val = entry.getValue();
                MetricRunner.dlog(key + " : " + val);
            }
        } catch (Exception e) {
            MetricRunner.dlog(e);
        }
    }

    public static int filterRange(Iterable<Tree> iter, PythonFileData fileData, boolean isSrc) {
        int count = 0;
        for (Tree t : iter) {
            if ((isSrc && !fileData.isSrcNodeInExtendedRange(t)) ||
                    (!isSrc && !fileData.isDstNodeInExtendedRange(t))) {
                continue;
            }
            count++;
        }
        return count;
    }

    public static void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier,
            PythonFileData fileData) {
        // MetricRunner.dlog("SRC---------------------------------------------------:\n"
        // + results.src);
        // MetricRunner.dlog("DST---------------------------------------------------:\n"
        // + results.dst);

        // #TODO filter these within range
        metrics.put("anyDeleted", filterRange(classifier.getDeletedSrcs(), fileData, true));
        metrics.put("anyInserted", filterRange(classifier.getInsertedDsts(), fileData, false));
        metrics.put("getMovedSrcs", filterRange(classifier.getMovedSrcs(), fileData, true));
        metrics.put("UpdatedSrcs", filterRange(classifier.getUpdatedSrcs(), fileData, true));

        // MetricRunner.dlog("calcDeletedIfStmts(classifier, metrics);");
        calcDeletedIfStmts(classifier, metrics, fileData);
        // MetricRunner.dlog("calcInsertedIfConditions(classifier, metrics);");
        calcInsertedIfConditions(classifier, metrics, fileData);
        // MetricRunner.dlog("getElseMetrics(results, classifier, metrics);");
        getElseMetrics(results, classifier, metrics, fileData);
    }

    public static void putHeaders(List<String> headers) {
        headers.add("anyDeleted");
        headers.add("anyInserted");
        headers.add("getMovedSrcs");
        headers.add("UpdatedSrcs");

        headers.add("elseInserted");
        headers.add("elseDeleted");
        headers.add("elseUpdated");

        headers.add("insertedIfConditions");

        headers.add("deletedIfStmts");
    }

    // else can appear as modified/updated/move on it's own without accompanying
    // parent being in the appropriate classifier.map
    // GUMtree will add both parent and child in the map If parent is
    // modified/updated
    // we only want the else aka child suites
    // to avoid overcounting we only check trees that are suite and cild to if
    public static int countElse(Iterable<Tree> iter, PythonFileData fileData, boolean isSrc) {
        int count = 0;
        for (Tree t : iter) {

            if (AstUtils.isTreeType(t, AstUtils.SUITE)) {
                Tree parent = t.getParent();
                if (AstUtils.isTreeType(parent, AstUtils.IF_STMT)) {
                    if ((isSrc && !fileData.isSrcNodeInExtendedRange(t)) ||
                            (!isSrc && !fileData.isInsertedNodeInExtendedRange(t))) {
                        continue;
                    }
                    count++;
                }
            }
        }

        return count;
    }

    public static void getElseMetrics(Diff results, TreeClassifier classifier, Map<String, Integer> metrics,
            PythonFileData fileData) {
        int elseInserted = countElse(classifier.getInsertedDsts(), fileData, false);
        int elseDeleted = countElse(classifier.getDeletedSrcs(), fileData, true);
        int elseUpdated = countElse(classifier.getUpdatedSrcs(), fileData, true);

        metrics.put("elseInserted", elseInserted);
        metrics.put("elseDeleted", elseDeleted);
        metrics.put("elseUpdated", elseUpdated);
    }

    private static void calcDeletedIfStmts(TreeClassifier classifier, Map<String, Integer> metrics,
            PythonFileData fileData) {
        int deletedIfStmts = 0;
        for (Tree t : classifier.getDeletedSrcs()) {
            if (fileData.isSrcNodeInExtendedRange(t)) {
                if (t.getType().name.equals("if_stmt")) {
                    deletedIfStmts++;
                    // MetricRunner.dlog((t.toTreeString()));
                    MetricRunner.dlog("deletion in extended range :\n" + t.toTreeString());

                }
            } else {
                MetricRunner.dlog("deletion out of range :\n" + t.toTreeString());
            }
        }
        metrics.put("deletedIfStmts", deletedIfStmts);
    }

    private static void calcInsertedIfConditions(TreeClassifier classifier, Map<String, Integer> metrics,
            PythonFileData fileData) {
        int insertedIfConditions = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if (t.getType().name.equals("if_stmt")) {

                if (fileData.isInsertedNodeInExtendedRange(t)) {
                    insertedIfConditions++;
                    MetricRunner.dlog("insertion in extended range :\n" + t.toTreeString());

                } else {
                    MetricRunner.dlog(fileData.getDstNodeParentOverlappingExtendedRange(t));
                    MetricRunner.dlog("insertion out of range :\n" + t.toTreeString());
                }

            }

            // MetricRunner.dlog(t);
            // MetricRunner.dlog("-----------");
            // MetricRunner.dlog(t.toTreeString());
        }
        metrics.put("insertedIfConditions", insertedIfConditions);

    }
}